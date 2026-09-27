import os
import re
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
import mysql.connector
import requests
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')


# Database connection helper
def get_db_connection():
  return mysql.connector.connect(
      host=os.getenv('MYSQL_HOST', 'localhost'),
      user=os.getenv('MYSQL_USER', 'root'),
      password=os.getenv('MYSQL_PASSWORD', ''),
      database=os.getenv('MYSQL_DB', 'portfolio_db'),
  )


@app.route('/')
def index():
  return send_from_directory('.', 'index.html')


# ---------------- USER AUTHENTICATION ---------------- #


@app.route('/api/signup', methods=['POST'])
def signup():
  data = request.get_json()
  email = data.get('email', '').strip().lower()
  password = data.get('password', '')

  if not email or not password:
    return jsonify({'error': 'Email and password required.'}), 400

  # Hash password securely
  hashed_pwd = generate_password_hash(password)

  try:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    if cursor.fetchone():
      return jsonify({'error': 'Account with this email already exists.'}), 400

    # Insert user into MySQL
    cursor.execute(
        'INSERT INTO users (email, password_hash) VALUES (%s, %s)',
        (email, hashed_pwd),
    )
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({'message': 'Account created successfully!'}), 201
  except Exception as e:
    return jsonify({'error': f'Database error: {str(e)}'}), 500


@app.route('/api/login', methods=['POST'])
def login():
  data = request.get_json()
  email = data.get('email', '').strip().lower()
  password = data.get('password', '')

  try:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    # Verify password hash
    if not user or not check_password_hash(user['password_hash'], password):
      return jsonify({'error': 'Invalid email or password.'}), 401

    return jsonify({
        'message': 'Login successful',
        'email': user['email'],
        'hasPortfolio': bool(user['portfolio_html']),
    })
  except Exception as e:
    return jsonify({'error': f'Database error: {str(e)}'}), 500


# ---------------- PORTFOLIO GENERATION & VIEW ---------------- #


@app.route('/api/generate-portfolio', methods=['POST'])
def generate_portfolio():
  try:
    api_key = os.getenv('gemini_key')
    if not api_key:
      return jsonify({'error': 'gemini_key is missing in .env'}), 500

    data = request.get_json()
    email = data.get('email', '').strip().lower()
    resume_text = data.get('resumeText', '')

    if not email or not resume_text:
      return jsonify({'error': 'Email and resume text are required.'}), 400

    prompt = (
        'Convert the following resume text into a clean, modern HTML portfolio'
        ' layout using inline CSS styling and clean tags like h1, h2, p, ul,'
        ' li. Do not wrap inside markdown backticks:\n\n'
        f'{resume_text}'
    )

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}'
    payload = {'contents': [{'parts': [{'text': prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()

    if response.status_code != 200:
      return jsonify({'error': 'Failed calling Gemini API.'}), response.status_code

    raw_text = response_data['candidates'][0]['content']['parts'][0]['text']
    clean_html = re.sub(r'```html|```', '', raw_text).strip()

    # Save portfolio directly into MySQL
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET portfolio_html = %s WHERE email = %s',
        (clean_html, email),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'portfolioHtml': clean_html})

  except Exception as e:
    return jsonify({'error': str(e)}), 500


@app.route('/api/get-portfolio', methods=['GET'])
def get_portfolio():
  email = request.args.get('email', '').strip().lower()
  if not email:
    return jsonify({'error': 'Email parameter required.'}), 400

  try:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'SELECT portfolio_html FROM users WHERE email = %s', (email,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not user['portfolio_html']:
      return jsonify({'portfolioHtml': None})

    return jsonify({'portfolioHtml': user['portfolio_html']})
  except Exception as e:
    return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)