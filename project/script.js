let isSignUpMode = false;
let currentUser = null;

const emailRegex = /^[^\s@]+@[^\s@]+\.com$/;
const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[a-zA-Z0-9!@#$\%^&*]{8,}$/;

function toggleAuthMode(event) {
    if (event) event.preventDefault();
    isSignUpMode = !isSignUpMode;

    document.getElementById('authTitle').innerText = isSignUpMode ? "Create Account" : "Sign In";
    document.getElementById('authSubtitle').innerText = isSignUpMode ? "Sign up to start converting your resume." : "Welcome back! Please enter your details.";
    document.getElementById('authSubmitBtn').innerText = isSignUpMode ? "Create Account" : "Sign In";
    document.getElementById('toggleText').innerText = isSignUpMode ? "Already have an account?" : "Don't have an account?";
    document.getElementById('toggleAuthBtn').innerText = isSignUpMode ? "Sign In" : "Create Account";
    document.getElementById('passwordHint').style.display = isSignUpMode ? "block" : "none";
    clearErrors();
}

function clearErrors() {
    document.getElementById('emailError').innerText = "";
    document.getElementById('passwordError').innerText = "";
}

async function handleAuth(event) {
    event.preventDefault();
    clearErrors();

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    let isValid = true;
    if (!emailRegex.test(email)) {
        document.getElementById('emailError').innerText = "Email must contain '@' and end with '.com'";
        isValid = false;
    }
    if (!passwordRegex.test(password)) {
        document.getElementById('passwordError').innerText = "Password must be at least 8 chars, contain 1 digit & 1 special symbol.";
        isValid = false;
    }
    if (!isValid) return;

    const endpoint = isSignUpMode ? '/api/signup' : '/api/login';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Authentication failed');
        }

        if (isSignUpMode) {
            alert("Account created successfully! Please sign in.");
            toggleAuthMode();
        } else {
            currentUser = email;
            openDashboard();
        }
    } catch (err) {
        document.getElementById('passwordError').innerText = err.message;
    }
}

function openDashboard() {
    document.getElementById('authView').classList.add('hidden');
    document.getElementById('dashboardView').classList.remove('hidden');
}

function signOut() {
    currentUser = null;
    document.getElementById('dashboardView').classList.add('hidden');
    document.getElementById('authView').classList.remove('hidden');
    document.getElementById('authForm').reset();
    hideSubSections();
}

function showSection(sectionId) {
    hideSubSections();
    document.getElementById(sectionId).classList.remove('hidden');

    if (sectionId === 'viewSection') {
        renderPortfolioView();
    }
}

function hideSubSections() {
    document.getElementById('uploadSection').classList.add('hidden');
    document.getElementById('viewSection').classList.add('hidden');
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('fileNameDisplay').innerText = file.name;
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('resumeTextInput').value = e.target.result;
        };
        reader.readAsText(file);
    }
}

async function generatePortfolio() {
    const resumeText = document.getElementById('resumeTextInput').value.trim();
    if (!resumeText) {
        alert("Please paste text or upload a text file with your resume details.");
        return;
    }

    const spinner = document.getElementById('loadingSpinner');
    const generateBtn = document.getElementById('generateBtn');

    spinner.classList.remove('hidden');
    generateBtn.disabled = true;

    try {
        const response = await fetch('/api/generate-portfolio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: currentUser, resumeText })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate portfolio.');
        }

        showSection('viewSection');
    } catch (err) {
        alert("Error generating portfolio: " + err.message);
    } finally {
        spinner.classList.add('hidden');
        generateBtn.disabled = false;
    }
}

async function renderPortfolioView() {
    const noPortfolioMsg = document.getElementById('noPortfolioMsg');
    const portfolioContent = document.getElementById('portfolioContent');
    const preview = document.getElementById('portfolioPreview');
    const linkInput = document.getElementById('portfolioLinkInput');

    try {
        const response = await fetch(`/api/get-portfolio?email=${encodeURIComponent(currentUser)}`);
        const data = await response.json();

        if (!data.portfolioHtml) {
            noPortfolioMsg.classList.remove('hidden');
            portfolioContent.classList.add('hidden');
        } else {
            noPortfolioMsg.classList.add('hidden');
            portfolioContent.classList.remove('hidden');

            linkInput.value = `${window.location.origin}/portfolio?user=${encodeURIComponent(currentUser)}`;
            preview.innerHTML = data.portfolioHtml;
        }
    } catch (err) {
        alert("Failed to load portfolio from database.");
    }
}

function copyPortfolioLink() {
    const linkInput = document.getElementById('portfolioLinkInput');
    linkInput.select();
    navigator.clipboard.writeText(linkInput.value);
    alert("Portfolio link copied to clipboard!");
}