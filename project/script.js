function switchTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const loginTabBtn = document.getElementById('loginTabBtn');
    const signupTabBtn = document.getElementById('signupTabBtn');

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        loginTabBtn.classList.add('active');
        signupTabBtn.classList.remove('active');
    } else {
        signupForm.classList.remove('hidden');
        loginForm.classList.add('hidden');
        signupTabBtn.classList.add('active');
        loginTabBtn.classList.remove('active');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('resume');
    const fileLabel = document.getElementById('fileLabel');
    const uploadForm = document.getElementById('uploadForm');
    const generateBtn = document.getElementById('generateBtn');

    if (dropArea && fileInput) {
        dropArea.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                fileLabel.innerHTML = `Selected File: <strong style="color:#38bdf8;">${fileInput.files[0].name}</strong>`;
            }
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropArea.style.backgroundColor = '#1e293b';
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropArea.style.backgroundColor = '#0f172a';
            }, false);
        });

        dropArea.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileLabel.innerHTML = `Selected File: <strong style="color:#38bdf8;">${files[0].name}</strong>`;
            }
        });
    }

    if (uploadForm && generateBtn) {
        uploadForm.addEventListener('submit', () => {
            generateBtn.classList.add('loading');
            generateBtn.innerText = 'Extracting Resume & Generating Portfolio... Please wait...';
        });
    }
});