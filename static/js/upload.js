/**
 * upload.js — Handles drag-and-drop file upload with validation and progress.
 */
document.addEventListener('DOMContentLoaded', () => {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('fileInput');
    const form = document.getElementById('uploadForm');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const removeBtn = document.getElementById('removeFile');
    const submitBtn = document.getElementById('submitBtn');
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const progressPct = document.getElementById('progressPercent');

    const ALLOWED = ['pdf', 'docx', 'txt'];
    const MAX_SIZE = 16 * 1024 * 1024;

    // Click to browse
    zone.addEventListener('click', () => input.click());

    // Drag events
    ['dragenter', 'dragover'].forEach(e => {
        zone.addEventListener(e, ev => { ev.preventDefault(); zone.classList.add('drag-over'); });
    });
    ['dragleave', 'drop'].forEach(e => {
        zone.addEventListener(e, ev => { ev.preventDefault(); zone.classList.remove('drag-over'); });
    });
    zone.addEventListener('drop', ev => {
        const files = ev.dataTransfer.files;
        if (files.length) handleFile(files[0]);
    });

    input.addEventListener('change', () => {
        if (input.files.length) handleFile(input.files[0]);
    });

    removeBtn.addEventListener('click', () => {
        input.value = '';
        fileInfo.style.display = 'none';
        submitBtn.disabled = true;
    });

    function handleFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!ALLOWED.includes(ext)) {
            alert('Unsupported file type. Please upload PDF, DOCX, or TXT.');
            return;
        }
        if (file.size > MAX_SIZE) {
            alert('File too large. Maximum size is 16 MB.');
            return;
        }

        // Transfer file to input
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;

        fileName.textContent = file.name;
        fileSize.textContent = formatSize(file.size);
        fileInfo.style.display = 'block';
        submitBtn.disabled = false;
    }

    // AJAX upload with progress
    form.addEventListener('submit', e => {
        e.preventDefault();
        if (!input.files.length) return;

        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();

        progressDiv.style.display = 'block';
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Uploading...';

        xhr.upload.addEventListener('progress', ev => {
            if (ev.lengthComputable) {
                const pct = Math.round((ev.loaded / ev.total) * 100);
                progressBar.style.width = pct + '%';
                progressPct.textContent = pct + '%';
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200 || xhr.status === 302) {
                // Follow redirect
                const redirect = xhr.responseURL || xhr.getResponseHeader('Location');
                if (redirect) {
                    window.location.href = redirect;
                } else {
                    // Parse redirect from HTML response
                    window.location.href = xhr.responseURL;
                }
            } else {
                alert('Upload failed. Please try again.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-cpu"></i> Process Document';
            }
        });

        xhr.addEventListener('error', () => {
            alert('Upload failed. Please check your connection.');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-cpu"></i> Process Document';
        });

        xhr.open('POST', form.action);
        xhr.send(formData);
    });

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
});
