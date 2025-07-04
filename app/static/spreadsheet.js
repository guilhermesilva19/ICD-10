// AI Medical Coding - Spreadsheet Interface JavaScript
class SpreadsheetProcessor {
    constructor() {
        this.files = [];
        this.results = [];
        this.isProcessing = false;
        this.currentFileIndex = 0;
        this.completedFiles = 0; // For tracking parallel progress
        
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        // Main elements
        this.fileInput = document.getElementById('fileInput');
        this.uploadArea = document.getElementById('uploadArea');
        this.fileList = document.getElementById('fileList');
        
        // Buttons
        this.selectFilesBtn = document.getElementById('selectFilesBtn');
        this.processBtn = document.getElementById('processBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.exportBtn = document.getElementById('exportBtn');
        this.newBatchBtn = document.getElementById('newBatchBtn');
        
        // Progress elements
        this.progressSection = document.getElementById('progressSection');
        this.progressBar = document.getElementById('progressBar');
        this.progressStats = document.getElementById('progressStats');
        this.currentProcessing = document.getElementById('currentProcessing');
        
        // Results elements
        this.resultsSection = document.getElementById('resultsSection');
        this.resultsTableBody = document.getElementById('resultsTableBody');
        this.totalFiles = document.getElementById('totalFiles');
        this.successCount = document.getElementById('successCount');
        this.errorCount = document.getElementById('errorCount');
        this.totalCodes = document.getElementById('totalCodes');
        
        // Modal elements
        this.exportModal = document.getElementById('exportModal');
        this.closeModal = document.querySelector('.close');
        this.exportCSV = document.getElementById('exportCSV');
        this.exportExcel = document.getElementById('exportExcel');
        this.exportJSON = document.getElementById('exportJSON');
    }

    bindEvents() {
        // File selection events
        this.selectFilesBtn.addEventListener('click', () => this.selectFiles());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelection(e));
        
        // Drag and drop events
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        this.uploadArea.addEventListener('click', () => this.selectFiles());
        
        // Control buttons
        this.processBtn.addEventListener('click', () => this.startProcessing());
        this.clearBtn.addEventListener('click', () => this.clearAll());
        this.newBatchBtn.addEventListener('click', () => this.newBatch());
        
        // Export events
        this.exportBtn.addEventListener('click', () => this.showExportModal());
        this.closeModal.addEventListener('click', () => this.hideExportModal());
        this.exportCSV.addEventListener('click', () => this.exportAsCSV());
        this.exportExcel.addEventListener('click', () => this.exportAsExcel());
        this.exportJSON.addEventListener('click', () => this.exportAsJSON());
        
        // Modal close on outside click
        window.addEventListener('click', (e) => {
            if (e.target === this.exportModal) {
                this.hideExportModal();
            }
        });
    }

    selectFiles() {
        this.fileInput.multiple = true;
        this.fileInput.click();
    }

    handleFileSelection(event) {
        const selectedFiles = Array.from(event.target.files);
        this.addFiles(selectedFiles);
    }

    handleDragOver(event) {
        event.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const droppedFiles = Array.from(event.dataTransfer.files);
        this.addFiles(droppedFiles);
    }

    addFiles(newFiles) {
        // Filter supported file types
        const supportedTypes = ['.txt', '.pdf', '.doc', '.docx', '.html', '.htm'];
        const validFiles = newFiles.filter(file => {
            const extension = '.' + file.name.split('.').pop().toLowerCase();
            return supportedTypes.includes(extension);
        });

        // Add valid files to the list (avoid duplicates)
        validFiles.forEach(file => {
            const isDuplicate = this.files.some(existingFile => 
                existingFile.name === file.name && existingFile.size === file.size
            );
            
            if (!isDuplicate) {
                this.files.push(file);
            }
        });

        this.updateFileList();
        this.updateProcessButton();

        // Show notification for invalid files
        const invalidCount = newFiles.length - validFiles.length;
        if (invalidCount > 0) {
            this.showNotification(`${invalidCount} files were skipped (unsupported format)`, 'warning');
        }

        if (validFiles.length > 0) {
            this.showNotification(`Added ${validFiles.length} files`, 'success');
        }
    }

    updateFileList() {
        if (this.files.length === 0) {
            this.fileList.innerHTML = '';
            return;
        }

        const fileListHTML = `
            <div style="background: var(--gray-50); border-radius: 10px; padding: 20px; margin-top: 20px;">
                <h4 style="margin-bottom: 15px; color: var(--gray-800);">
                    <i class="fas fa-list"></i> Selected Files (${this.files.length})
                </h4>
                <div style="max-height: 200px; overflow-y: auto;">
                    ${this.files.map((file, index) => `
                        <div style="display: flex; justify-content: between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--gray-200);">
                            <div style="flex: 1;">
                                <i class="fas fa-file-medical" style="color: var(--primary-color); margin-right: 8px;"></i>
                                <span style="font-weight: 500;">${file.name}</span>
                                <span style="color: var(--gray-600); margin-left: 10px;">(${this.formatFileSize(file.size)})</span>
                            </div>
                            <button onclick="processor.removeFile(${index})" 
                                    style="background: var(--danger-color); color: white; border: none; border-radius: 5px; padding: 4px 8px; cursor: pointer; font-size: 0.8rem;">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        this.fileList.innerHTML = fileListHTML;
    }

    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
        this.updateProcessButton();
    }

    updateProcessButton() {
        this.processBtn.disabled = this.files.length === 0 || this.isProcessing;
    }

    async startProcessing() {
        if (this.files.length === 0 || this.isProcessing) return;

        this.isProcessing = true;
        this.results = [];
        this.currentFileIndex = 0;
        this.completedFiles = 0; // For tracking parallel progress

        // Show progress section
        this.progressSection.style.display = 'block';
        this.resultsSection.style.display = 'none';

        // Reset progress and stats
        this.updateProgress(0, this.files.length);
        this.progressBar.style.width = '0%';
        this.currentProcessing.innerHTML = `
            <div class="processing-file">
                <div class="spinner"></div>
                <span>processing...</span>
            </div>
        `;

        // Clear previous results and create placeholder rows for all files
        this.resultsTableBody.innerHTML = '';
        this.files.forEach((file, index) => {
            this.createPlaceholderRow(file, index);
        });

        // Fire all requests in parallel
        const promises = this.files.map((file, index) => this.processFile(file, index));
        
        // Wait for all promises to settle (either resolve or reject)
        await Promise.allSettled(promises);

        // Show final results
        this.showResults();
        this.isProcessing = false;
        this.updateProcessButton();
    }

    createPlaceholderRow(file, index) {
        const row = document.createElement('tr');
        row.id = `result-row-${index}`; // Assign a unique ID to each row
        row.innerHTML = `
            <td class="col-filepath">${file.webkitRelativePath || file.name}</td>
            <td colspan="6" style="color: var(--gray-600);">Waiting to process...</td>
            <td><i class="fas fa-clock status-processing"></i> Queued</td>
        `;
        this.resultsTableBody.appendChild(row);
    }

    async processFile(file, index) {
        // Update placeholder row to "processing"
        const rowToUpdate = document.getElementById(`result-row-${index}`);
        rowToUpdate.innerHTML = `
            <td class="col-filepath">${file.webkitRelativePath || file.name}</td>
            <td colspan="6" style="color: var(--warning-color);">
                <div class="spinner" style="display: inline-block; vertical-align: middle; margin-right: 8px;"></div>
                Processing...
            </td>
            <td><i class="fas fa-cogs status-processing"></i> Processing</td>
        `;

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/process-spreadsheet', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            // **OVERRIDE FILEPATH FROM FRONTEND**
            result.filepath = file.webkitRelativePath || file.name;

            if (response.ok) {
                result.status = 'completed';
                result.error = null;
                this.updateResultRow(index, result, 'success');
            } else {
                result.status = 'error';
                result.error = result.detail || 'Processing failed';
                this.updateResultRow(index, result, 'error');
            }
            this.results.push(result);

        } catch (error) {
            const errorResult = {
                filepath: file.webkitRelativePath || file.name,
                title: 'Client-side Error',
                status: 'error',
                error: error.message
            };
            this.updateResultRow(index, errorResult, 'error');
            this.results.push(errorResult);
        } finally {
            // Update overall progress after each file is done
            this.completedFiles++;
            this.updateProgress(this.completedFiles, this.files.length);
            this.progressBar.style.width = `${(this.completedFiles / this.files.length) * 100}%`;
        }
    }

    updateResultRow(index, result, type) {
        const row = document.getElementById(`result-row-${index}`);
        if (!row) return;

        const statusIcon = type === 'success' 
            ? '<i class="fas fa-check-circle status-completed"></i>' 
            : '<i class="fas fa-exclamation-circle status-error"></i>';

        const genderBadge = result.gender ? 
            `<span class="gender-badge gender-${result.gender.toLowerCase()}">${result.gender}</span>` : 'N/A';

        row.innerHTML = `
            <td class="col-filepath">${result.filepath}</td>
            <td class="col-title">${result.title || 'N/A'}</td>
            <td class="col-gender">${genderBadge}</td>
            <td>${result.unique_name || 'N/A'}</td>
            <td class="col-keywords">${result.keywords || 'N/A'}</td>
            <td class="col-diagnosis">${result.diagnosis_codes || (type === 'error' ? result.error : 'None Found')}</td>
            <td class="col-language">${result.language || 'N/A'}</td>
            <td>${statusIcon} ${result.status}</td>
        `;
    }

    showCurrentProcessing(filename) {
        this.currentProcessing.innerHTML = `
            <div class="processing-file">
                <div class="spinner"></div>
                <span>Processing: ${filename}</span>
            </div>
        `;
    }

    addResultRow(result, type) {
        const row = document.createElement('tr');
        row.className = type === 'error' ? 'animate__animated animate__fadeInUp' : 'animate__animated animate__fadeInUp';
        
        const statusIcon = type === 'success' ? 
            '<i class="fas fa-check-circle status-completed"></i>' : 
            '<i class="fas fa-exclamation-circle status-error"></i>';

        const genderBadge = result.gender ? 
            `<span class="gender-badge gender-${result.gender.toLowerCase()}">${result.gender}</span>` : '';

        row.innerHTML = `
            <td class="col-filepath">${result.filepath}</td>
            <td class="col-title">${result.title}</td>
            <td class="col-gender">${genderBadge}</td>
            <td>${result.unique_name}</td>
            <td class="col-keywords">${result.keywords}</td>
            <td class="col-diagnosis">${result.diagnosis_codes}</td>
            <td class="col-language">${result.language}</td>
            <td>${statusIcon} ${result.status}</td>
        `;

        this.resultsTableBody.appendChild(row);
    }

    updateProgress(current, total) {
        this.progressStats.textContent = `${current} / ${total} completed`;
        if (current === total) {
            this.currentProcessing.innerHTML = `
                <div class="processing-file" style="background-color: #d1fae5; border-left-color: var(--success-color);">
                    <i class="fas fa-check-circle" style="color: var(--success-color);"></i>
                    <span>All files processed!</span>
                </div>
            `;
        }
    }

    showResults() {
        this.progressSection.style.display = 'none';
        this.resultsSection.style.display = 'block';

        // Update statistics
        const successful = this.results.filter(r => r.status === 'completed').length;
        const errors = this.results.filter(r => r.status === 'error').length;
        const totalCodes = this.results.reduce((sum, r) => {
            if (r.diagnosis_codes) {
                return sum + r.diagnosis_codes.split(',').filter(code => code.trim()).length;
            }
            return sum;
        }, 0);

        this.totalFiles.textContent = this.results.length;
        this.successCount.textContent = successful;
        this.errorCount.textContent = errors;
        this.totalCodes.textContent = totalCodes;

        // Show success notification
        this.showNotification(`Processing completed! ${successful} successful, ${errors} errors`, 'success');
    }

    clearAll() {
        this.files = [];
        this.results = [];
        this.updateFileList();
        this.updateProcessButton();
        this.progressSection.style.display = 'none';
        this.resultsSection.style.display = 'none';
        this.showNotification('All files cleared', 'info');
    }

    newBatch() {
        this.clearAll();
        this.fileInput.value = '';
    }

    // Export functionality
    showExportModal() {
        if (this.results.length === 0) {
            this.showNotification('No results to export', 'warning');
            return;
        }
        this.exportModal.style.display = 'block';
    }

    hideExportModal() {
        this.exportModal.style.display = 'none';
    }

    exportAsCSV() {
        const csvContent = this.convertToCSV(this.results);
        this.downloadFile(csvContent, 'medical_coding_results.csv', 'text/csv');
        this.hideExportModal();
        this.showNotification('CSV exported successfully', 'success');
    }

    exportAsExcel() {
        const workbook = XLSX.utils.book_new();
        const worksheet = XLSX.utils.json_to_sheet(this.results);
        
        // Set column widths
        const colWidths = [
            { wch: 30 }, // filepath
            { wch: 40 }, // title
            { wch: 10 }, // gender
            { wch: 30 }, // unique_name
            { wch: 50 }, // keywords
            { wch: 30 }, // diagnosis_codes
            { wch: 10 }, // language
            { wch: 15 }  // status
        ];
        worksheet['!cols'] = colWidths;

        XLSX.utils.book_append_sheet(workbook, worksheet, 'Medical Coding Results');
        XLSX.writeFile(workbook, 'medical_coding_results.xlsx');
        
        this.hideExportModal();
        this.showNotification('Excel file exported successfully', 'success');
    }

    exportAsJSON() {
        const jsonContent = JSON.stringify(this.results, null, 2);
        this.downloadFile(jsonContent, 'medical_coding_results.json', 'application/json');
        this.hideExportModal();
        this.showNotification('JSON exported successfully', 'success');
    }

    convertToCSV(data) {
        if (data.length === 0) return '';

        const headers = ['Filepath', 'Title', 'Gender', 'Unique Name', 'Keywords', 'Diagnosis Codes', 'Language', 'Status'];
        const csvRows = [headers.join(',')];

        data.forEach(row => {
            const values = [
                this.escapeCSVField(row.filepath),
                this.escapeCSVField(row.title),
                this.escapeCSVField(row.gender),
                this.escapeCSVField(row.unique_name),
                this.escapeCSVField(row.keywords),
                this.escapeCSVField(row.diagnosis_codes),
                this.escapeCSVField(row.language),
                this.escapeCSVField(row.status)
            ];
            csvRows.push(values.join(','));
        });

        return csvRows.join('\n');
    }

    escapeCSVField(field) {
        if (field === null || field === undefined) return '';
        const stringField = String(field);
        if (stringField.includes(',') || stringField.includes('"') || stringField.includes('\n')) {
            return `"${stringField.replace(/"/g, '""')}"`;
        }
        return stringField;
    }

    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 10px;
            color: white;
            font-weight: 600;
            z-index: 10000;
            max-width: 300px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            animation: slideInRight 0.3s ease;
        `;

        // Set background color based on type
        const colors = {
            success: '#059669',
            error: '#dc2626',
            warning: '#d97706',
            info: '#2563eb'
        };
        notification.style.backgroundColor = colors[type] || colors.info;

        // Set icon based on type
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        const icon = icons[type] || icons.info;

        notification.innerHTML = `
            <i class="${icon}" style="margin-right: 10px;"></i>
            ${message}
        `;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize the processor when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Create one instance and assign it to the global scope
    // so that inline onclick handlers can access it.
    window.processor = new SpreadsheetProcessor();
}); 