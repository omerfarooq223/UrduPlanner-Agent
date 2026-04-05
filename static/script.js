/* ============================================================================
   UrduPlanner - Frontend Logic
   ============================================================================ */

// State management
const state = {
    templatePath: null,
    textbookPath: null,
    maxPages: null,
    outputFile: null,
    isProcessing: false
};

// DOM Elements
const templateInput = document.getElementById('template-input');
const textbookInput = document.getElementById('textbook-input');
const validateBtn = document.getElementById('validate-btn');
const validationMessage = document.getElementById('validation-message');

const fileUploadSection = document.querySelector('.file-upload-section');
const formSection = document.querySelector('.form-section');
const planningForm = document.getElementById('planning-form');

const progressSection = document.querySelector('.progress-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const statusMessage = document.getElementById('status-message');

const resultSection = document.querySelector('.result-section');
const successMessage = document.getElementById('success-message');
const downloadBtn = document.getElementById('download-btn');
const createAnotherBtn = document.getElementById('create-another-btn');

const errorSection = document.querySelector('.error-section');
const errorMessage = document.getElementById('error-message');
const retryBtn = document.getElementById('retry-btn');

// ============================================================================
// File Upload Handling
// ============================================================================

function updateFileName(input, displayId) {
    const fileName = input.files.length > 0 ? input.files[0].name : '';
    const displayElement = document.getElementById(displayId);
    
    if (fileName) {
        displayElement.textContent = `✓ ${fileName}`;
        displayElement.className = 'file-name';
    } else {
        displayElement.textContent = '';
    }
}

templateInput.addEventListener('change', (e) => {
    updateFileName(e.target, 'template-name');
});

textbookInput.addEventListener('change', (e) => {
    updateFileName(e.target, 'textbook-name');
});

// Drag and drop functionality
function setupDragAndDrop(input, box) {
    box.addEventListener('dragover', (e) => {
        e.preventDefault();
        box.classList.add('drag-over');
    });

    box.addEventListener('dragleave', () => {
        box.classList.remove('drag-over');
    });

    box.addEventListener('drop', (e) => {
        e.preventDefault();
        box.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length > 0) {
            input.files = e.dataTransfer.files;
            const event = new Event('change', { bubbles: true });
            input.dispatchEvent(event);
        }
    });
}

const templateBox = document.querySelector('.upload-box:nth-child(1)');
const textbookBox = document.querySelector('.upload-box:nth-child(2)');

setupDragAndDrop(templateInput, templateBox);
setupDragAndDrop(textbookInput, textbookBox);

// ============================================================================
// File Validation
// ============================================================================

validateBtn.addEventListener('click', async () => {
    validationMessage.textContent = '';
    validationMessage.className = 'message'; 
    
    if (!templateInput.files.length || !textbookInput.files.length) {
        showMessage(validationMessage, 'Please select both files', 'error');
        return;
    }

    validateBtn.disabled = true;
    validateBtn.textContent = 'Validating...';

    try {
        const formData = new FormData();
        formData.append('template', templateInput.files[0]);
        formData.append('textbook', textbookInput.files[0]);

        const response = await fetch('/api/validate-files', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showMessage(validationMessage, data.error || 'Validation failed', 'error');
            return;
        }

        state.templatePath = data.template_path;
        state.textbookPath = data.textbook_path;
        state.maxPages = data.max_pages;

        showMessage(validationMessage, `✓ Files validated! PDF has ${data.max_pages} pages.`, 'success');

        // Show form section
        setTimeout(() => {
            fileUploadSection.style.display = 'none';
            formSection.style.display = 'block';
            formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 500);

    } catch (error) {
        console.error('Validation error:', error);
        showMessage(validationMessage, 'Validation error: ' + error.message, 'error');
    } finally {
        validateBtn.disabled = false;
        validateBtn.textContent = 'Validate Files';
    }
});

// ============================================================================
// Form Submission & Plan Generation
// ============================================================================

planningForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const week = document.getElementById('week-input').value.trim();
    const unit = document.getElementById('unit-input').value.trim();
    const dates = document.getElementById('dates-input').value.trim();
    const pages = document.getElementById('pages-input').value.trim();
    const subject = document.getElementById('subject-input').value.trim();

    if (!week || !unit || !dates || !pages) {
        alert('Please fill in all required fields');
        return;
    }

    // Show progress section
    formSection.style.display = 'none';
    progressSection.style.display = 'block';
    errorSection.style.display = 'none';
    resultSection.style.display = 'none';

    state.isProcessing = true;
    updateProgress(0, 'Starting generation...');

    try {
        const payload = {
            week: week,
            unit_number: unit,
            dates: dates,
            pages: pages,
            subject: subject,
            template_path: state.templatePath,
            textbook_path: state.textbookPath
        };

        // Simulate progress updates
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 20;
                updateProgress(
                    Math.min(progress, 90),
                    'Processing with Ollama (this can take 3-10 minutes for larger pages)...'
                );
            }
        }, 500);

        const response = await fetch('/api/generate-plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        clearInterval(progressInterval);
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Generation failed');
        }

        // Success!
        state.outputFile = data.output_file;
        updateProgress(100, 'Complete!');

        setTimeout(() => {
            progressSection.style.display = 'none';
            resultSection.style.display = 'block';
            successMessage.textContent = data.message || 'Your lesson plan has been generated successfully!';
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 500);

    } catch (error) {
        console.error('Generation error:', error);
        clearInterval(progressInterval);
        
        progressSection.style.display = 'none';
        errorSection.style.display = 'block';
        errorMessage.textContent = error.message;
        errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } finally {
        state.isProcessing = false;
    }
});

// ============================================================================
// Progress Management
// ============================================================================

function updateProgress(percent, message) {
    progressFill.style.width = percent + '%';
    progressText.textContent = message + ' (' + Math.round(percent) + '%)';
}

// ============================================================================
// Download
// ============================================================================

downloadBtn.addEventListener('click', () => {
    if (!state.outputFile) {
        alert('No file to download');
        return;
    }

    const downloadLink = document.createElement('a');
    downloadLink.href = `/api/download/${encodeURIComponent(state.outputFile)}`;
    downloadLink.download = state.outputFile;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
});

// ============================================================================
// Reset & Create Another
// ============================================================================

createAnotherBtn.addEventListener('click', () => {
    resetForm();
});

retryBtn.addEventListener('click', () => {
    resetForm();
});

function resetForm() {
    // Reset all inputs
    templateInput.value = '';
    textbookInput.value = '';
    document.getElementById('week-input').value = '';
    document.getElementById('unit-input').value = '';
    document.getElementById('dates-input').value = '';
    document.getElementById('pages-input').value = '';
    document.getElementById('subject-input').value = 'Urdu';
    
    document.getElementById('template-name').textContent = '';
    document.getElementById('textbook-name').textContent = '';
    validationMessage.textContent = '';

    // Reset state
    state.templatePath = null;
    state.textbookPath = null;
    state.maxPages = null;
    state.outputFile = null;
    state.isProcessing = false;

    // Show file upload section
    fileUploadSection.style.display = 'block';
    formSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';

    fileUploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================================================
// Utility Functions
// ============================================================================

function showMessage(element, text, type) {
    element.textContent = text;
    element.className = `message ${type}`;
}

// ============================================================================
// Page Load
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('UrduPlanner Frontend loaded');
});
