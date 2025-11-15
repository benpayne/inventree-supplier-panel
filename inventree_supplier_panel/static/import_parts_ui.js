/**
 * Import Parts UI for Supplier Cart Plugin
 * 
 * This module provides a UI for importing complete parts (InvenTree part + manufacturer + supplier part)
 * from Digikey or Mouser using just a supplier SKU.
 */

/**
 * Render the main import parts page
 */
export function renderImportPartsPage(target, data) {
    if (!target) {
        console.error("No target provided to renderImportPartsPage");
        return;
    }

    console.log("Rendering Import Parts page");

    // Fetch categories for the dropdown
    fetchCategories().then(categories => {
        renderPageContent(target, categories);
    }).catch(error => {
        console.error('Error fetching categories:', error);
        target.innerHTML = `
            <div class="alert alert-danger">
                Failed to load categories. Please check your permissions and try again.
            </div>
        `;
    });
}

/**
 * Fetch part categories from InvenTree API
 */
async function fetchCategories() {
    const response = await fetch('/api/part/category/');
    if (!response.ok) {
        throw new Error(`Failed to fetch categories: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
}

/**
 * Render the page content
 */
function renderPageContent(target, categories) {
    target.innerHTML = `
        <div class="import-parts-container">
            <style>
                .import-parts-container {
                    max-width: 800px;
                    margin: 20px auto;
                    padding: 20px;
                }
                .import-form {
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .form-group {
                    margin-bottom: 20px;
                }
                .form-group label {
                    display: block;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: #333;
                }
                .form-group select,
                .form-group input {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }
                .form-group input:focus,
                .form-group select:focus {
                    outline: none;
                    border-color: #007bff;
                    box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
                }
                .import-btn {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                .import-btn:hover {
                    background: #0056b3;
                }
                .import-btn:disabled {
                    background: #6c757d;
                    cursor: not-allowed;
                }
                .spinner {
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #007bff;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    animation: spin 1s linear infinite;
                    display: inline-block;
                    margin-left: 10px;
                    vertical-align: middle;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .result-area {
                    margin-top: 20px;
                    display: none;
                }
                .result-area.show {
                    display: block;
                }
                .alert {
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 15px;
                }
                .alert-success {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                }
                .alert-danger {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                }
                .alert-info {
                    background-color: #d1ecf1;
                    border: 1px solid #bee5eb;
                    color: #0c5460;
                }
                .part-details {
                    background: white;
                    padding: 15px;
                    border-radius: 4px;
                    margin-top: 10px;
                }
                .part-details h4 {
                    margin-top: 0;
                    color: #333;
                }
                .part-details .detail-row {
                    display: flex;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }
                .part-details .detail-label {
                    font-weight: 600;
                    width: 200px;
                    color: #666;
                }
                .part-details .detail-value {
                    flex: 1;
                    color: #333;
                }
                .view-part-btn {
                    display: inline-block;
                    margin-top: 15px;
                    padding: 10px 20px;
                    background: #28a745;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: 600;
                }
                .view-part-btn:hover {
                    background: #218838;
                    color: white;
                    text-decoration: none;
                }
            </style>
            
            <h2><i class="fas fa-package-import"></i> Import Parts from Supplier</h2>
            <p>Import a complete part from Digikey or Mouser using just the supplier SKU. 
               The system will automatically create the InvenTree part, manufacturer, and all relationships.</p>
            
            <div class="import-form">
                <div class="form-group">
                    <label for="supplier-select">Supplier</label>
                    <select id="supplier-select">
                        <option value="digikey">Digikey</option>
                        <option value="mouser">Mouser</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="sku-input">Supplier Part Number (SKU)</label>
                    <input 
                        id="sku-input" 
                        type="text" 
                        placeholder="e.g., 296-21752-2-ND"
                        autocomplete="off"
                    >
                </div>
                
                <div class="form-group">
                    <label for="category-select">Part Category</label>
                    <select id="category-select">
                        <option value="">Select a category...</option>
                        ${renderCategoryOptions(categories)}
                    </select>
                </div>
                
                <button class="import-btn" id="import-btn">
                    <i class="fas fa-download"></i> Import Part
                </button>
                <span id="loading-spinner" style="display: none;" class="spinner"></span>
            </div>
            
            <div class="result-area" id="result-area">
                <!-- Results will be displayed here -->
            </div>
        </div>
    `;

    // Set up event listeners
    const importBtn = target.querySelector('#import-btn');
    const skuInput = target.querySelector('#sku-input');
    
    importBtn.addEventListener('click', () => importPart(target));
    
    // Allow Enter key to submit
    skuInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            importPart(target);
        }
    });
}

/**
 * Render category options recursively to show hierarchy
 */
function renderCategoryOptions(categories, level = 0) {
    if (!categories || !Array.isArray(categories)) {
        return '';
    }
    
    let html = '';
    const indent = '&nbsp;&nbsp;'.repeat(level);
    
    for (const category of categories) {
        html += `<option value="${category.pk}">${indent}${category.name}</option>`;
        
        // Recursively add subcategories if they exist
        if (category.subcategories && category.subcategories.length > 0) {
            html += renderCategoryOptions(category.subcategories, level + 1);
        }
    }
    
    return html;
}

/**
 * Import a part from the selected supplier
 */
async function importPart(target) {
    const supplierSelect = target.querySelector('#supplier-select');
    const skuInput = target.querySelector('#sku-input');
    const categorySelect = target.querySelector('#category-select');
    const importBtn = target.querySelector('#import-btn');
    const loadingSpinner = target.querySelector('#loading-spinner');
    const resultArea = target.querySelector('#result-area');

    const supplier = supplierSelect.value;
    const sku = skuInput.value.trim();
    const category_pk = categorySelect.value;

    // Validation
    if (!sku) {
        showResult(resultArea, 'danger', 'Please enter a supplier part number (SKU)');
        return;
    }
    
    if (!category_pk) {
        showResult(resultArea, 'danger', 'Please select a part category');
        return;
    }

    // Disable button and show spinner
    importBtn.disabled = true;
    loadingSpinner.style.display = 'inline-block';
    showResult(resultArea, 'info', `Importing part ${sku} from ${supplier.charAt(0).toUpperCase() + supplier.slice(1)}...`);

    try {
        const response = await fetch('/plugin/suppliercart/importfullpart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                supplier: supplier,
                sku: sku,
                category_pk: parseInt(category_pk)
            })
        });

        const data = await response.json();

        // Hide spinner
        loadingSpinner.style.display = 'none';
        importBtn.disabled = false;

        if (response.ok && data.status === 'success') {
            // Show success message with part details
            showSuccessResult(resultArea, data);
            
            // Clear the SKU input for next import
            skuInput.value = '';
        } else {
            // Show error message
            const errorMsg = data.message || data.error || 'Unknown error occurred';
            showResult(resultArea, 'danger', `Error: ${errorMsg}`);
        }
    } catch (error) {
        loadingSpinner.style.display = 'none';
        importBtn.disabled = false;
        showResult(resultArea, 'danger', `Error: ${error.message}`);
        console.error('Import error:', error);
    }
}

/**
 * Show a result message
 */
function showResult(resultArea, type, message) {
    resultArea.className = 'result-area show';
    resultArea.innerHTML = `
        <div class="alert alert-${type}">
            ${message}
        </div>
    `;
}

/**
 * Show success result with part details
 */
function showSuccessResult(resultArea, data) {
    resultArea.className = 'result-area show';
    resultArea.innerHTML = `
        <div class="alert alert-success">
            <strong>Success!</strong> Part imported successfully.
        </div>
        <div class="part-details">
            <h4>Created Part Details</h4>
            <div class="detail-row">
                <div class="detail-label">Part Name:</div>
                <div class="detail-value">${data.part_name || 'N/A'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Manufacturer:</div>
                <div class="detail-value">${data.manufacturer_name || 'N/A'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">MPN:</div>
                <div class="detail-value">${data.mpn || 'N/A'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Supplier:</div>
                <div class="detail-value">${data.supplier_name || 'N/A'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">SKU:</div>
                <div class="detail-value">${data.sku || 'N/A'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Description:</div>
                <div class="detail-value">${data.description || 'N/A'}</div>
            </div>
            <a href="/web/part/${data.part_pk}/" class="view-part-btn">
                <i class="fas fa-eye"></i> View Part in InvenTree
            </a>
        </div>
    `;
}

/**
 * Get CSRF token from cookies
 */
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

