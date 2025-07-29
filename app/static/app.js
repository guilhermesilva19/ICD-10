document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').innerHTML = '';
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayResults(result);
        } else {
            displayError(result.detail || 'Analysis failed');
        }
    } catch (error) {
        displayError('Network error: ' + error.message);
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
});

function displayResults(data) {
    let html = '<div class="container"><h2>📊 AI Medical Coding Results</h2>';
    
    // Document Information
    html += `<div class="result-box">
        <h3>📄 Document: ${data.title}</h3>
        <p><strong>🔍 Keywords:</strong> ${data.enriched_keywords}</p>
        <p><strong>📊 Total Codes Found:</strong> ${data.total_codes_found}</p>
    </div>`;
    
    // ICD Codes Summary
    if (data.diagnosis_codes && data.diagnosis_codes.length > 0) {
        html += '<div class="result-box">';
        html += '<h3>🎯 ICD-10-CM Diagnosis Codes</h3>';
        html += '<p><strong>Codes:</strong> ' + data.diagnosis_codes.join(', ') + '</p>';
        html += '</div>';
    }
    
    // Enhanced Code Details
    if (data.code_details && data.code_details.length > 0) {
        html += '<h3>✅ Detailed Code Analysis</h3>';
        html += '<div class="confidence-comparison-header">';
        html += '<p><strong>📊 Confidence Score Comparison:</strong> Legacy (Original) vs Improved (Multi-factor)</p>';
        html += '</div>';
        data.code_details.forEach(code => {
            const legacyConfidenceNum = parseInt(code.confidence.replace('%', ''));
            const improvedConfidenceNum = parseInt(code.improved_confidence.replace('%', ''));
            
            // Use improved confidence for styling if available
            const displayConfidenceNum = code.improved_confidence ? improvedConfidenceNum : legacyConfidenceNum;
            
            html += `<div class="code ${getConfidenceClass(displayConfidenceNum)}">
                <h4>🏥 ${code.code}</h4>
                <div class="confidence-scores">
                    <div class="score legacy ${getScoreClass(legacyConfidenceNum)}">Legacy: ${code.confidence}</div>
                    <div class="score improved ${getScoreClass(improvedConfidenceNum)}">Improved: ${code.improved_confidence}</div>
                </div>
                <p><strong>Description:</strong> ${code.enhanced_description}</p>
            </div>`;
        });
    }
    
    // Clinical Summary
    if (data.clinical_summary) {
        html += `<div class="result-box" style="background: #f0f9ff; border-left-color: #3b82f6;">
            <h4>🩺 Clinical Summary</h4>
            <p>${data.clinical_summary}</p>
        </div>`;
    }
    
    // No results message
    if (!data.code_details || data.code_details.length === 0) {
        html += '<div class="result-box" style="border-left-color: #dc3545;"><p>❌ No relevant ICD codes found. Please review the document or try with more detailed medical information.</p></div>';
    }
    
    html += '</div>';
    document.getElementById('results').innerHTML = html;
}

function displayError(message) {
    document.getElementById('results').innerHTML = 
        `<div class="container"><div class="result-box" style="border-left-color: #dc3545;">
            <h3>❌ Error</h3><p>${message}</p>
        </div></div>`;
}

function getScoreClass(confidence) {
    if (confidence >= 70) return 'high';
    if (confidence >= 50) return 'medium';
    return 'low';
}

function getConfidenceClass(confidence) {
    if (confidence >= 70) return 'high-confidence';
    if (confidence >= 50) return 'medium-confidence';
    return 'low-confidence';
} 