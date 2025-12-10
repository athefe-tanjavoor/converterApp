// FileConverter Pro - Client-side JavaScript

// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const filesContainer = document.getElementById('files-container');
const clearFilesBtn = document.getElementById('clear-files');
const formatSection = document.getElementById('format-section');
const targetFormat = document.getElementById('target-format');
const convertBtn = document.getElementById('convert-btn');
const progressSection = document.getElementById('progress-section');
const progressFill = document.getElementById('progress-fill');
const progressStatus = document.getElementById('progress-status');
const taskIdDisplay = document.getElementById('task-id-display');
const resultSection = document.getElementById('result-section');
const successCard = document.getElementById('success-card');
const errorCard = document.getElementById('error-card');
const resultMessage = document.getElementById('result-message');
const errorMessage = document.getElementById('error-message');
const downloadBtn = document.getElementById('download-btn');
const convertAnotherBtn = document.getElementById('convert-another');
const tryAgainBtn = document.getElementById('try-again');

// State
let selectedFiles = [];
let currentTaskId = null;
let pollingInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupThemeToggle();
    setupEventListeners();
});

// Theme Toggle Logic
function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const iconSpan = themeToggle.querySelector('.icon');
    
    // Check saved preference
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme, iconSpan);

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme, iconSpan);
    });
}

function updateThemeIcon(theme, iconSpan) {
    if (theme === 'light') {
        iconSpan.textContent = '🌙'; // Moon for light mode
    } else {
        iconSpan.textContent = '☀️'; // Sun for dark mode
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Upload zone click
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    // Clear files
    clearFilesBtn.addEventListener('click', clearFiles);
    
    // Convert button
    convertBtn.addEventListener('click', startConversion);
    
    // Download button
    downloadBtn.addEventListener('click', downloadFile);
    
    // Reset buttons
    convertAnotherBtn.addEventListener('click', resetApp);
    tryAgainBtn.addEventListener('click', resetApp);
}

// Handle Files
function handleFiles(files) {
    if (files.length === 0) return;
    
    selectedFiles = Array.from(files);
    displayFiles();
    fileList.style.display = 'block';
    formatSection.style.display = 'block';
}

// Display Files
function displayFiles() {
    filesContainer.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const fileName = document.createElement('span');
        fileName.className = 'file-name';
        fileName.textContent = file.name;
        
        const fileSize = document.createElement('span');
        fileSize.className = 'file-size';
        fileSize.textContent = formatFileSize(file.size);
        
        fileItem.appendChild(fileName);
        fileItem.appendChild(fileSize);
        filesContainer.appendChild(fileItem);
    });
}

// Format File Size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Clear Files
function clearFiles() {
    selectedFiles = [];
    filesContainer.innerHTML = '';
    fileList.style.display = 'none';
    formatSection.style.display = 'none';
    fileInput.value = '';
}

// Start Conversion
async function startConversion() {
    const format = targetFormat.value;
    
    if (!format) {
        alert('Please select a target format');
        return;
    }
    
    if (selectedFiles.length === 0) {
        alert('Please select files to convert');
        return;
    }
    
    // Hide upload section
    uploadZone.style.display = 'none';
    fileList.style.display = 'none';
    formatSection.style.display = 'none';
    
    // Show progress
    progressSection.style.display = 'block';
    progressStatus.textContent = 'Uploading files...';
    progressFill.style.width = '10%';
    
    try {
        // Create FormData
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        formData.append('target_format', format);
        
        // Upload files
        const response = await fetch('/convert', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        currentTaskId = data.task_id;
        
        // Update progress
        progressStatus.textContent = 'Processing conversion...';
        progressFill.style.width = '30%';
        taskIdDisplay.textContent = currentTaskId;
        
        // Start polling
        startPolling();
        
    } catch (error) {
        showError(error.message);
    }
}

// Start Polling
function startPolling() {
    pollingInterval = setInterval(checkTaskStatus, 2000);
}

// Stop Polling
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Check Task Status
async function checkTaskStatus() {
    try {
        const response = await fetch(`/status/${currentTaskId}`);
        const data = await response.json();
        
        if (data.status === 'PENDING' || data.status === 'STARTED') {
            progressFill.style.width = '60%';
            progressStatus.textContent = data.message || 'Processing...';
        }
        else if (data.status === 'SUCCESS') {
            stopPolling();
            progressFill.style.width = '100%';
            progressStatus.textContent = 'Conversion complete!';
            
            setTimeout(() => {
                showSuccess(data.result);
            }, 500);
        }
        else if (data.status === 'FAILURE') {
            stopPolling();
            showError(data.error || 'Conversion failed');
        }
        
    } catch (error) {
        stopPolling();
        showError('Error checking status: ' + error.message);
    }
}

// Show Success
function showSuccess(result) {
    progressSection.style.display = 'none';
    resultSection.style.display = 'block';
    successCard.style.display = 'block';
    errorCard.style.display = 'none';
    
    const outputType = result.output?.type;
    const filesCount = result.output?.files_count || 1;
    
    if (outputType === 'zip') {
        resultMessage.textContent = `Successfully converted ${filesCount} files! Download the ZIP archive below.`;
    } else {
        resultMessage.textContent = 'File converted successfully! Click below to download.';
    }
}

// Show Error
function showError(message) {
    progressSection.style.display = 'none';
    resultSection.style.display = 'block';
    successCard.style.display = 'none';
    errorCard.style.display = 'block';
    
    errorMessage.textContent = message;
}

// Download File
function downloadFile() {
    if (!currentTaskId) return;
    
    // Create download link
    const downloadLink = document.createElement('a');
    downloadLink.href = `/download/${currentTaskId}`;
    downloadLink.download = '';  // Use server-provided filename
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Reset App
function resetApp() {
    // Clear state
    selectedFiles = [];
    currentTaskId = null;
    stopPolling();
    
    // Reset UI
    uploadZone.style.display = 'block';
    fileList.style.display = 'none';
    formatSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    
    filesContainer.innerHTML = '';
    fileInput.value = '';
    targetFormat.value = '';
    progressFill.style.width = '0%';
}
