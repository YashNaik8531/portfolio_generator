import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from dotenv import load_dotenv
import google.generativeai as genai
from werkzeug.security import generate_password_hash, check_password_hash
from pypdf import PdfReader

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-998877")

# Configure Gemini API
GENAI_KEY = os.getenv("gemini_key")
if GENAI_KEY:
    genai.configure(api_key=GENAI_KEY)

# Safe MySQL Connection Helper
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DB", "portfolio_db"),
            port=int(os.getenv("MYSQL_PORT", 3306))
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return None

# Database Table Initialization
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    extracted_text LONGTEXT,
                    generated_content LONGTEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Database Init Error: {err}")

init_db()

SYSTEM_PROMPT = """
You are an expert Executive Resume Writer, Technical Recruiter, and Senior Front-End Engineer.
Analyze the provided raw resume text and auto-extract all key details (Candidate Name, Role, Email, Skills, Work Experience, Projects).

Generate a COMPLETE, self-contained HTML page with embedded CSS styling for an executive portfolio.

CRITICAL DESIGN & CONTENT GUIDELINES:
1. DESIGN & THEME:
   - Modern, sleek dark-mode tech aesthetic (Background: #0F172A, Primary Text: #F8FAFC, Accents: #38BDF8, #818CF8).
   - Responsive layout with glassmorphism hover effects and clear card divisions.
2. RECRUITER-FOCUSED COPYWRITING:
   - Rephrase achievements into impact-driven statements using active verbs (e.g., 'Engineered', 'Architected', 'Optimized').
   - Structure projects using the STAR method (Situation, Task, Action, Result).
3. REQUIRED SECTIONS TO GENERATE:
   - HERO SECTION: Candidate Name, Job Title, elevator pitch, 'Download Resume' CTA, 'Contact Me' CTA.
   - SKILLS GRID: Group skills cleanly into visually distinct badges or cards.
   - WORK & PROJECTS: High-converting project/experience cards detailing impact, technologies, and achievements.
   - ABOUT ME: A compelling professional summary.
   - FOOTER/CONTACT: Contact details and social links extracted from the resume.

STRICT FORMATTING RULE:
- Output ONLY the raw HTML code starting with <!DOCTYPE html> and ending with </html>.
- DO NOT wrap the output in markdown code blocks (```html ... ```) or write conversational text.
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()

    if not email or not password:
        flash("Please provide both email and password.", "error")
        return redirect(url_for('index'))

    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_pw))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Account created successfully! Please login.", "success")
        except mysql.connector.Error:
            flash("Email already registered or database error.", "error")
    else:
        flash("Database connection failed.", "error")

    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            flash("Logged in successfully!", "success")
        else:
            flash("Invalid email or password.", "error")
    else:
        flash("Database connection failed.", "error")

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
def generate_portfolio():
    if 'user_id' not in session:
        flash("Please login to generate your portfolio.", "error")
        return redirect(url_for('index'))

    if 'resume' not in request.files:
        flash("No file uploaded. Please select a PDF resume.", "error")
        return redirect(url_for('index'))

    file = request.files['resume']
    if file.filename == '' or not file.filename.endswith('.pdf'):
        flash("Please upload a valid PDF file.", "error")
        return redirect(url_for('index'))

    try:
        reader = PdfReader(file)
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
    except Exception as e:
        print(f"PDF Extraction Error: {e}")
        flash("Failed to read PDF file.", "error")
        return redirect(url_for('index'))

    if not extracted_text.strip():
        flash("Could not extract text from PDF. Ensure it is not an image scan.", "error")
        return redirect(url_for('index'))

    full_prompt = f"{SYSTEM_PROMPT}\n\nCandidate Resume Text:\n{extracted_text}"

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(full_prompt)
        generated_html = response.text.strip()

        if generated_html.startswith("```"):
            lines = generated_html.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            generated_html = "\n".join(lines).strip()

    except Exception as e:
        print(f"Gemini API Error: {e}")
        flash("AI Portfolio generation failed. Check your API key.", "error")
        return redirect(url_for('index'))

    user_id = session['user_id']
    portfolio_id = None
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO portfolios (user_id, extracted_text, generated_content) VALUES (%s, %s, %s)",
                (user_id, extracted_text, generated_html)
            )
            conn.commit()
            portfolio_id = cursor.lastrowid
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"MySQL Insert Error: {err}")

    if portfolio_id:
        return redirect(url_for('view_portfolio', portfolio_id=portfolio_id))
    else:
        return generated_html

@app.route('/portfolio/<int:portfolio_id>')
def view_portfolio(portfolio_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    conn = get_db_connection()
    if not conn:
        return "Database connection error.", 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT generated_content FROM portfolios WHERE id = %s AND user_id = %s", (portfolio_id, session['user_id']))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result.get('generated_content'):
            return result['generated_content']
        else:
            return "Portfolio not found or unauthorized.", 404
    except mysql.connector.Error as err:
        return f"Database error: {err}", 500

if __name__ == '__main__':
    app.run(debug=True)