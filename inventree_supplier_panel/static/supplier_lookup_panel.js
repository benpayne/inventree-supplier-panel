/**
 * Supplier Lookup Panel for Supplier Cart Plugin
 * 
 * This module provides UI components for looking up and adding supplier parts
 * to InvenTree parts from Digikey, Mouser, and Farnell.
 */

/**
 * Render the supplier lookup panel
 */
export function renderPanel(target, data) {
    if (!target) {
        console.error("No target provided to supplier lookup panel");
        return;
    }

    const partPk = data.context?.part_pk || data.id;

    // Fetch the plugin settings to get registered suppliers
    fetchRegisteredSuppliers(partPk).then(suppliers => {
        renderPanelContent(target, partPk, suppliers);
    }).catch(error => {
        console.error('Error fetching registered suppliers:', error);
        target.innerHTML = `
            <div class="alert alert-danger">
                Failed to load supplier information. Please check plugin settings.
            </div>
        `;
    });
}

/**
 * Fetch registered suppliers from the plugin settings
 */
async function fetchRegisteredSuppliers(partPk) {
    // Fetch the supplier PKs from the plugin settings API
    try {
        const response = await fetch('/api/plugins/suppliercart/settings/');
        if (!response.ok) {
            throw new Error('Failed to fetch plugin settings');
        }
        
        const settings = await response.json();
        const suppliers = [];
        
        // Map settings to supplier list
        if (settings.DIGIKEY_PK) {
            suppliers.push({ name: 'Digikey', value: settings.DIGIKEY_PK, key: 'digikey' });
        }
        if (settings.MOUSER_PK) {
            suppliers.push({ name: 'Mouser', value: settings.MOUSER_PK, key: 'mouser' });
        }
        if (settings.FARNELL_PK) {
            suppliers.push({ name: 'Farnell', value: settings.FARNELL_PK, key: 'farnell' });
        }
        
        return suppliers;
    } catch (error) {
        console.error('Error fetching supplier settings:', error);
        // Fallback to showing all suppliers, but they won't work without PKs
        return [
            { name: 'Digikey', value: '', key: 'digikey' },
            { name: 'Mouser', value: '', key: 'mouser' },
            { name: 'Farnell', value: '', key: 'farnell' }
        ];
    }
}

/**
 * Render the panel content
 */
function renderPanelContent(target, partPk, suppliers) {
    target.innerHTML = `
        <div class="supplier-lookup-panel">
            <style>
                .wheel {
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    animation: spin 2s linear infinite;
                    visibility: hidden;
                    display: inline-block;
                    margin-left: 10px;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .supplier-lookup-form {
                    margin-top: 15px;
                }
                .supplier-lookup-form table {
                    width: 100%;
                }
                .supplier-lookup-form td {
                    padding: 8px;
                }
                .supplier-lookup-form select,
                .supplier-lookup-form input[type="text"] {
                    width: 100%;
                    padding: 6px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            </style>
            
            <div class='alert alert-block' id='result-${partPk}' style='display: none;'>&nbsp;</div>
            <div id="loader-${partPk}" class="wheel"></div>
            
            <div class="supplier-lookup-form">
                <table class='table table-condensed'>
                    <tbody>
                        <tr>
                            <td><label for="supplier-${partPk}">Select Supplier</label></td>
                            <td>
                                <select id="supplier-${partPk}">
                                    ${suppliers.map(s => `<option value="${s.value}">${s.name}</option>`).join('')}
                                </select>
                            </td>
                        </tr>
                        <tr>
                            <td><label for="sku-${partPk}">Supplier Part Number</label></td>
                            <td>
                                <input id="sku-${partPk}" type="text" value="" 
                                       placeholder="Enter exact SKU from supplier website">
                            </td>
                        </tr>
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="2">
                                <button type="button" class="btn btn-primary" id="add-part-btn-${partPk}">
                                    <span class="fas fa-plus"></span> Add Supplier Part
                                </button>
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
    `;

    // Set up the add part button click handler
    const addPartBtn = target.querySelector(`#add-part-btn-${partPk}`);
    addPartBtn.addEventListener('click', () => addSupplierPart(partPk));

    // Allow Enter key to submit
    const skuInput = target.querySelector(`#sku-${partPk}`);
    skuInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addSupplierPart(partPk);
        }
    });
}

/**
 * Add a supplier part to the InvenTree part
 */
async function addSupplierPart(partPk) {
    const skuInput = document.getElementById(`sku-${partPk}`);
    const supplierSelect = document.getElementById(`supplier-${partPk}`);
    const loader = document.getElementById(`loader-${partPk}`);
    const result = document.getElementById(`result-${partPk}`);
    const addPartBtn = document.getElementById(`add-part-btn-${partPk}`);

    const sku = skuInput.value.trim();
    const supplier = supplierSelect.value;

    if (!sku) {
        result.textContent = 'Please enter a supplier part number';
        result.className = 'alert alert-block alert-warning';
        result.style.display = 'block';
        return;
    }

    // Show loader, disable button
    loader.style.visibility = 'visible';
    addPartBtn.disabled = true;
    result.style.display = 'none';

    try {
        // Prepare data for API call
        const data = {
            sku: sku,
            supplier: supplier,
            pk: partPk
        };

        // Call the backend API endpoint
        const response = await fetch('/plugin/suppliercart/addsupplierpart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        const responseData = await response.json();

        // Hide loader
        loader.style.visibility = 'hidden';
        addPartBtn.disabled = false;

        // Show result message
        result.textContent = responseData.message || 'Unknown response';
        result.style.display = 'block';

        if (responseData.message === 'OK' || response.ok) {
            result.className = 'alert alert-block alert-success';
            // Clear the SKU input on success
            skuInput.value = '';
            
            // Optionally reload the page to show the new supplier part
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            result.className = 'alert alert-block alert-danger';
        }
    } catch (error) {
        loader.style.visibility = 'hidden';
        addPartBtn.disabled = false;
        result.textContent = `Error: ${error.message}`;
        result.className = 'alert alert-block alert-danger';
        result.style.display = 'block';
        console.error('Add supplier part error:', error);
    }
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

