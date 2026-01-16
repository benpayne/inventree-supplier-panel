/**
 * Purchase Order Transfer Panel for Supplier Cart Plugin
 * 
 * This module provides UI components for transferring Purchase Orders
 * to supplier shopping carts (Digikey and Mouser).
 */

/**
 * Render the Digikey PO transfer panel
 */
export function renderDigikeyPanel(target, data) {
    if (!target) {
        console.error("No target provided to renderDigikeyPanel");
        return;
    }

    const poPk = data.context?.po_pk || data.id;
    renderPanel(target, data, poPk, 'Digikey');
}

/**
 * Render the Mouser PO transfer panel
 */
export function renderMouserPanel(target, data) {
    if (!target) {
        console.error("No target provided to renderMouserPanel");
        return;
    }

    const poPk = data.context?.po_pk || data.id;
    renderPanel(target, data, poPk, 'Mouser');
}

/**
 * Common panel rendering function for both suppliers
 */
function renderPanel(target, data, poPk, supplierName) {
    // Build import order section HTML for Digikey
    const digikeyImportSection = supplierName === 'Digikey' ? `
            <hr>
            <h5>Import Order from Digikey</h5>
            <p class="text-muted">After placing your order on Digikey, import the actual prices and order number back into this PO.</p>

            <div id="order-select-container-${poPk}" style="margin-bottom: 10px;">
                <label for="order-select-${poPk}">Select Digikey Order:</label>
                <select class="form-control" id="order-select-${poPk}" style="max-width: 400px; display: inline-block; margin-left: 10px;">
                    <option value="">Loading orders...</option>
                </select>
                <button type='button' class='btn btn-sm btn-outline-secondary' id='refresh-orders-btn-${poPk}' title='Refresh order list' style="margin-left: 5px;">
                    <span class='fas fa-sync'></span>
                </button>
            </div>
            <div id="order-manual-container-${poPk}" style="margin-bottom: 10px;">
                <label for="order-manual-${poPk}">Or enter Order ID manually:</label>
                <input type="text" class="form-control" id="order-manual-${poPk}"
                       placeholder="e.g., 96611225" style="max-width: 200px; display: inline-block; margin-left: 10px;">
            </div>

            <button type='button' class='btn btn-success' id='import-order-btn-${poPk}' title='Import order data from Digikey'>
                <span class='fas fa-download'></span> Import Order
            </button>
            <div width="30px" id="import-loader-${poPk}" class="wheel"></div>
            <div class='alert alert-block' id='import-result-${poPk}' style='display: none;'>&nbsp;</div>
            <div id="import-details-${poPk}" style='display: none;'>
                <b>Digikey Order:</b> <span id="dk-order-id-${poPk}"></span><br>
                <b>Matched Items:</b> <span id="matched-count-${poPk}"></span><br>
                <div id="tracking-info-${poPk}" style="margin-top: 10px;"></div>
            </div>
            <div id="import-table-${poPk}"></div>

            <hr>
            <h5>Add Extra Costs</h5>
            <p class="text-muted">Manually add shipping, tax, and tariff costs as extra line items.</p>
            <div class="row" style="max-width: 600px;">
                <div class="col-4">
                    <label for="shipping-cost-${poPk}">Shipping ($):</label>
                    <input type="number" step="0.01" class="form-control" id="shipping-cost-${poPk}" placeholder="0.00">
                </div>
                <div class="col-4">
                    <label for="tax-cost-${poPk}">Tax ($):</label>
                    <input type="number" step="0.01" class="form-control" id="tax-cost-${poPk}" placeholder="0.00">
                </div>
                <div class="col-4">
                    <label for="tariff-cost-${poPk}">Tariff ($):</label>
                    <input type="number" step="0.01" class="form-control" id="tariff-cost-${poPk}" placeholder="0.00">
                </div>
            </div>
            <button type='button' class='btn btn-secondary' id='add-costs-btn-${poPk}' title='Add extra costs to PO' style="margin-top: 10px;">
                <span class='fas fa-plus'></span> Add Extra Costs
            </button>
            <div class='alert alert-block' id='costs-result-${poPk}' style='display: none; margin-top: 10px;'>&nbsp;</div>

            <hr>
            <h5>Digikey Authentication</h5>
            <p class="text-muted">If you're getting token errors, regenerate your Digikey OAuth token.</p>
            <button type='button' class='btn btn-warning' id='regen-token-btn-${poPk}' title='Regenerate Digikey OAuth token'>
                <span class='fas fa-key'></span> Regenerate Token
            </button>
    ` : '';

    // Build import order section HTML for Mouser
    const mouserImportSection = supplierName === 'Mouser' ? `
            <hr>
            <h5>Import Order from Mouser</h5>
            <p class="text-muted">After placing your order on Mouser, import the actual prices and order number back into this PO.</p>

            <div id="mouser-order-select-container-${poPk}" style="margin-bottom: 10px;">
                <label for="mouser-order-select-${poPk}">Select Mouser Order:</label>
                <select class="form-control" id="mouser-order-select-${poPk}" style="max-width: 400px; display: inline-block; margin-left: 10px;">
                    <option value="">Loading orders...</option>
                </select>
                <button type='button' class='btn btn-sm btn-outline-secondary' id='mouser-refresh-orders-btn-${poPk}' title='Refresh order list' style="margin-left: 5px;">
                    <span class='fas fa-sync'></span>
                </button>
            </div>
            <div id="mouser-order-manual-container-${poPk}" style="margin-bottom: 10px;">
                <label for="mouser-order-manual-${poPk}">Or enter Order Number manually:</label>
                <input type="text" class="form-control" id="mouser-order-manual-${poPk}"
                       placeholder="e.g., 1234567890" style="max-width: 200px; display: inline-block; margin-left: 10px;">
            </div>

            <button type='button' class='btn btn-success' id='mouser-import-order-btn-${poPk}' title='Import order data from Mouser'>
                <span class='fas fa-download'></span> Import Order
            </button>
            <div width="30px" id="mouser-import-loader-${poPk}" class="wheel"></div>
            <div class='alert alert-block' id='mouser-import-result-${poPk}' style='display: none;'>&nbsp;</div>
            <div id="mouser-import-details-${poPk}" style='display: none;'>
                <b>Mouser Order:</b> <span id="mouser-order-id-${poPk}"></span><br>
                <b>Matched Items:</b> <span id="mouser-matched-count-${poPk}"></span><br>
            </div>
            <div id="mouser-import-table-${poPk}"></div>

            <hr>
            <h5>Add Extra Costs</h5>
            <p class="text-muted">Manually add shipping and tax costs as extra line items.</p>
            <div class="row" style="max-width: 400px;">
                <div class="col-6">
                    <label for="mouser-shipping-cost-${poPk}">Shipping ($):</label>
                    <input type="number" step="0.01" class="form-control" id="mouser-shipping-cost-${poPk}" placeholder="0.00">
                </div>
                <div class="col-6">
                    <label for="mouser-tax-cost-${poPk}">Tax ($):</label>
                    <input type="number" step="0.01" class="form-control" id="mouser-tax-cost-${poPk}" placeholder="0.00">
                </div>
            </div>
            <button type='button' class='btn btn-secondary' id='mouser-add-costs-btn-${poPk}' title='Add extra costs to PO' style="margin-top: 10px;">
                <span class='fas fa-plus'></span> Add Extra Costs
            </button>
            <div class='alert alert-block' id='mouser-costs-result-${poPk}' style='display: none; margin-top: 10px;'>&nbsp;</div>
    ` : '';

    // Create the panel HTML structure
    target.innerHTML = `
        <div class="supplier-cart-panel">
            <style>
                table.align-right-6th-column th:nth-child(6), td:nth-child(6) {
                    text-align: right;
                }
                table.align-right-7th-column th:nth-child(7), td:nth-child(7) {
                    text-align: right;
                }
                table th {
                    padding: 8px;
                }
                .wheel {
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    animation: spin 2s linear infinite;
                    visibility: hidden;
                    display: inline-block;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>

            <button type='button' class='btn btn-primary' id='transfer-btn-${poPk}' title='Transfer PO to ${supplierName}'>
                <span class='fas fa-redo-alt'></span> Transfer PO
            </button>
            <br><br>
            <div width="30px" id="loader-${poPk}" class="wheel"></div>
            <div class='alert alert-block' id='result-${poPk}' style='display: none;'>&nbsp;</div>
            <div id="cart-info-${poPk}" style='display: none;'>
                <b>Created supplier key:</b> <span id="cart_key-${poPk}"></span><br>
                <b>Cart date:</b> <span id="cart_date-${poPk}"></span><br>
            </div>
            <div id="myDynamicTable-${poPk}"></div>
            ${digikeyImportSection}
            ${mouserImportSection}
        </div>
    `;

    // Set up the transfer button click handler
    const transferBtn = target.querySelector(`#transfer-btn-${poPk}`);
    transferBtn.addEventListener('click', () => transferCart(poPk, supplierName));

    // Load existing cart data if available from PO metadata
    if (data.instance?.metadata?.SupplierCart) {
        displayCartData(poPk, data.instance.metadata.SupplierCart);
    }

    // Set up Digikey-specific import order handlers
    if (supplierName === 'Digikey') {
        setupDigikeyImportOrderHandlers(poPk);
        setupDigikeyExtraCostsHandlers(poPk);
        setupTokenRegenHandler(poPk, data.context?.oauth_url);
    }

    // Set up Mouser-specific import order handlers
    if (supplierName === 'Mouser') {
        setupMouserImportOrderHandlers(poPk);
        setupMouserExtraCostsHandlers(poPk);
    }
}

/**
 * Set up event handlers for Digikey import order section
 */
function setupDigikeyImportOrderHandlers(poPk) {
    const importBtn = document.getElementById(`import-order-btn-${poPk}`);
    const refreshBtn = document.getElementById(`refresh-orders-btn-${poPk}`);

    // Load orders on init
    loadDigikeyOrders(poPk);

    // Refresh button handler
    refreshBtn.addEventListener('click', () => loadDigikeyOrders(poPk));

    // Import button click handler
    importBtn.addEventListener('click', () => importDigikeyOrder(poPk));
}

/**
 * Set up event handlers for Digikey extra costs section
 */
function setupDigikeyExtraCostsHandlers(poPk) {
    const addCostsBtn = document.getElementById(`add-costs-btn-${poPk}`);
    addCostsBtn.addEventListener('click', () => addDigikeyExtraCosts(poPk));
}

/**
 * Set up event handlers for Mouser import order section
 */
function setupMouserImportOrderHandlers(poPk) {
    const importBtn = document.getElementById(`mouser-import-order-btn-${poPk}`);
    const refreshBtn = document.getElementById(`mouser-refresh-orders-btn-${poPk}`);

    // Load orders on init
    loadMouserOrders(poPk);

    // Refresh button handler
    refreshBtn.addEventListener('click', () => loadMouserOrders(poPk));

    // Import button click handler
    importBtn.addEventListener('click', () => importMouserOrder(poPk));
}

/**
 * Set up event handlers for Mouser extra costs section
 */
function setupMouserExtraCostsHandlers(poPk) {
    const addCostsBtn = document.getElementById(`mouser-add-costs-btn-${poPk}`);
    addCostsBtn.addEventListener('click', () => addMouserExtraCosts(poPk));
}

/**
 * Set up event handler for token regeneration button
 */
function setupTokenRegenHandler(poPk, oauthUrl) {
    const regenBtn = document.getElementById(`regen-token-btn-${poPk}`);
    if (regenBtn && oauthUrl) {
        regenBtn.addEventListener('click', () => {
            window.open(oauthUrl, 'digikey-auth', 'width=800,height=600');
        });
    }
}

/**
 * Add extra costs (shipping, tax, tariff) to the PO - Digikey version
 */
async function addDigikeyExtraCosts(poPk) {
    const shippingInput = document.getElementById(`shipping-cost-${poPk}`);
    const taxInput = document.getElementById(`tax-cost-${poPk}`);
    const tariffInput = document.getElementById(`tariff-cost-${poPk}`);
    const result = document.getElementById(`costs-result-${poPk}`);
    const addCostsBtn = document.getElementById(`add-costs-btn-${poPk}`);

    const shipping = parseFloat(shippingInput.value) || 0;
    const tax = parseFloat(taxInput.value) || 0;
    const tariff = parseFloat(tariffInput.value) || 0;

    if (shipping === 0 && tax === 0 && tariff === 0) {
        result.textContent = 'Please enter at least one cost value';
        result.className = 'alert alert-block alert-warning';
        result.style.display = 'block';
        return;
    }

    addCostsBtn.disabled = true;

    try {
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        const response = await fetch(`/plugin/suppliercart/addextracosts/${poPk}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || '',
            },
            body: JSON.stringify({
                shipping: shipping,
                tax: tax,
                tariff: tariff
            })
        });
        const data = await response.json();

        addCostsBtn.disabled = false;

        if (data.message === 'OK') {
            result.textContent = `Added extra costs: ${data.added_lines.join(', ')}`;
            result.className = 'alert alert-block alert-success';
            result.style.display = 'block';
            // Clear inputs after success
            shippingInput.value = '';
            taxInput.value = '';
            tariffInput.value = '';
        } else {
            result.textContent = data.message || 'Failed to add extra costs';
            result.className = 'alert alert-block alert-danger';
            result.style.display = 'block';
        }
    } catch (error) {
        addCostsBtn.disabled = false;
        result.textContent = `Error: ${error.message}`;
        result.className = 'alert alert-block alert-danger';
        result.style.display = 'block';
        console.error('Add extra costs error:', error);
    }
}

/**
 * Load Digikey orders into the dropdown
 */
async function loadDigikeyOrders(poPk) {
    const orderSelect = document.getElementById(`order-select-${poPk}`);
    orderSelect.innerHTML = '<option value="">Loading orders...</option>';

    try {
        const response = await fetch('/plugin/suppliercart/digikeyorders/');
        const data = await response.json();

        if (data.message !== 'OK') {
            orderSelect.innerHTML = `<option value="">Error: ${data.message}</option>`;
            return;
        }

        if (!data.orders || data.orders.length === 0) {
            orderSelect.innerHTML = '<option value="">No recent orders found</option>';
            return;
        }

        orderSelect.innerHTML = '';
        data.orders.forEach(order => {
            const option = document.createElement('option');
            option.value = order.salesorder_id;
            const dateStr = order.date_entered ? new Date(order.date_entered).toLocaleDateString() : '';
            option.textContent = `${order.salesorder_id} - ${dateStr} ${order.purchase_order ? '(' + order.purchase_order + ')' : ''}`;
            orderSelect.appendChild(option);
        });
    } catch (error) {
        orderSelect.innerHTML = `<option value="">Error loading orders</option>`;
        console.error('Error loading Digikey orders:', error);
    }
}

/**
 * Import order data from Digikey
 */
async function importDigikeyOrder(poPk) {
    const orderSelect = document.getElementById(`order-select-${poPk}`);
    const orderManual = document.getElementById(`order-manual-${poPk}`);
    const loader = document.getElementById(`import-loader-${poPk}`);
    const result = document.getElementById(`import-result-${poPk}`);
    const importBtn = document.getElementById(`import-order-btn-${poPk}`);
    const importDetails = document.getElementById(`import-details-${poPk}`);

    // Get order ID from dropdown or manual input (manual takes precedence if filled)
    let salesorderId = orderManual.value.trim();
    if (!salesorderId) {
        salesorderId = orderSelect.value;
    }

    if (!salesorderId) {
        result.textContent = 'Please select or enter a Digikey order ID';
        result.className = 'alert alert-block alert-warning';
        result.style.display = 'block';
        return;
    }

    const requestBody = { salesorder_id: salesorderId };

    // Show loader, disable button
    loader.style.visibility = 'visible';
    importBtn.disabled = true;
    result.style.display = 'none';
    importDetails.style.display = 'none';

    try {
        // Get CSRF token from cookie
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        const response = await fetch(`/plugin/suppliercart/importorder/${poPk}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || '',
            },
            body: JSON.stringify(requestBody)
        });
        const data = await response.json();

        // Hide loader
        loader.style.visibility = 'hidden';
        importBtn.disabled = false;

        if (data.message === 'OK') {
            result.textContent = `Successfully imported order ${data.salesorder_id}`;
            result.className = 'alert alert-block alert-success';
            result.style.display = 'block';

            // Show import details
            importDetails.style.display = 'block';
            document.getElementById(`dk-order-id-${poPk}`).textContent = data.salesorder_id;
            document.getElementById(`matched-count-${poPk}`).textContent =
                `${data.matched_count} matched, ${data.unmatched_count} unmatched`;

            // Display tracking info if available
            const trackingDiv = document.getElementById(`tracking-info-${poPk}`);
            if (data.tracking && data.tracking.carrier) {
                let trackingHtml = `<b>Tracking:</b> ${data.tracking.carrier} - `;
                if (data.tracking.tracking_url) {
                    trackingHtml += `<a href="${data.tracking.tracking_url}" target="_blank">${data.tracking.tracking_number}</a>`;
                } else {
                    trackingHtml += data.tracking.tracking_number;
                }
                trackingHtml += `<br><b>Shipping Method:</b> ${data.tracking.shipping_method || 'N/A'}`;
                if (data.tracking.delivery_date) {
                    trackingHtml += `<br><b>Delivery Date:</b> ${data.tracking.delivery_date}`;
                }
                trackingDiv.innerHTML = trackingHtml;
            }

            // Display the import results table
            if (data.matched_items && data.matched_items.length > 0) {
                createImportResultsTable(poPk, data);
            }
        } else {
            result.textContent = data.message || 'Import failed';
            result.className = 'alert alert-block alert-danger';
            result.style.display = 'block';
        }
    } catch (error) {
        loader.style.visibility = 'hidden';
        importBtn.disabled = false;
        result.textContent = `Error: ${error.message}`;
        result.className = 'alert alert-block alert-danger';
        result.style.display = 'block';
        console.error('Import order error:', error);
    }
}

/**
 * Load Mouser orders into the dropdown
 */
async function loadMouserOrders(poPk) {
    const orderSelect = document.getElementById(`mouser-order-select-${poPk}`);
    orderSelect.innerHTML = '<option value="">Loading orders...</option>';

    try {
        const response = await fetch('/plugin/suppliercart/mouserorders/');
        const data = await response.json();

        if (data.message !== 'OK') {
            orderSelect.innerHTML = `<option value="">Error: ${data.message}</option>`;
            return;
        }

        if (!data.orders || data.orders.length === 0) {
            orderSelect.innerHTML = '<option value="">No recent orders found</option>';
            return;
        }

        orderSelect.innerHTML = '';
        data.orders.forEach(order => {
            const option = document.createElement('option');
            option.value = order.order_number;
            const dateStr = order.date_entered ? new Date(order.date_entered).toLocaleDateString() : '';
            option.textContent = `${order.order_number} - ${dateStr} ${order.po_number ? '(' + order.po_number + ')' : ''}`;
            orderSelect.appendChild(option);
        });
    } catch (error) {
        orderSelect.innerHTML = `<option value="">Error loading orders</option>`;
        console.error('Error loading Mouser orders:', error);
    }
}

/**
 * Import order data from Mouser
 */
async function importMouserOrder(poPk) {
    const orderSelect = document.getElementById(`mouser-order-select-${poPk}`);
    const orderManual = document.getElementById(`mouser-order-manual-${poPk}`);
    const loader = document.getElementById(`mouser-import-loader-${poPk}`);
    const result = document.getElementById(`mouser-import-result-${poPk}`);
    const importBtn = document.getElementById(`mouser-import-order-btn-${poPk}`);
    const importDetails = document.getElementById(`mouser-import-details-${poPk}`);

    // Get order number from dropdown or manual input (manual takes precedence if filled)
    let orderNumber = orderManual.value.trim();
    if (!orderNumber) {
        orderNumber = orderSelect.value;
    }

    if (!orderNumber) {
        result.textContent = 'Please select or enter a Mouser order number';
        result.className = 'alert alert-block alert-warning';
        result.style.display = 'block';
        return;
    }

    const requestBody = { order_number: orderNumber };

    // Show loader, disable button
    loader.style.visibility = 'visible';
    importBtn.disabled = true;
    result.style.display = 'none';
    importDetails.style.display = 'none';

    try {
        // Get CSRF token from cookie
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        const response = await fetch(`/plugin/suppliercart/importmouserorder/${poPk}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || '',
            },
            body: JSON.stringify(requestBody)
        });
        const data = await response.json();

        // Hide loader
        loader.style.visibility = 'hidden';
        importBtn.disabled = false;

        if (data.message === 'OK') {
            result.textContent = `Successfully imported order ${data.order_number}`;
            result.className = 'alert alert-block alert-success';
            result.style.display = 'block';

            // Show import details
            importDetails.style.display = 'block';
            document.getElementById(`mouser-order-id-${poPk}`).textContent = data.order_number;
            document.getElementById(`mouser-matched-count-${poPk}`).textContent =
                `${data.matched_count} matched, ${data.unmatched_count} unmatched`;

            // Display the import results table
            if (data.matched_items && data.matched_items.length > 0) {
                createMouserImportResultsTable(poPk, data);
            }
        } else {
            result.textContent = data.message || 'Import failed';
            result.className = 'alert alert-block alert-danger';
            result.style.display = 'block';
        }
    } catch (error) {
        loader.style.visibility = 'hidden';
        importBtn.disabled = false;
        result.textContent = `Error: ${error.message}`;
        result.className = 'alert alert-block alert-danger';
        result.style.display = 'block';
        console.error('Import Mouser order error:', error);
    }
}

/**
 * Add extra costs (shipping, tax) to the PO - Mouser version
 */
async function addMouserExtraCosts(poPk) {
    const shippingInput = document.getElementById(`mouser-shipping-cost-${poPk}`);
    const taxInput = document.getElementById(`mouser-tax-cost-${poPk}`);
    const result = document.getElementById(`mouser-costs-result-${poPk}`);
    const addCostsBtn = document.getElementById(`mouser-add-costs-btn-${poPk}`);

    const shipping = parseFloat(shippingInput.value) || 0;
    const tax = parseFloat(taxInput.value) || 0;

    if (shipping === 0 && tax === 0) {
        result.textContent = 'Please enter at least one cost value';
        result.className = 'alert alert-block alert-warning';
        result.style.display = 'block';
        return;
    }

    addCostsBtn.disabled = true;

    try {
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        const response = await fetch(`/plugin/suppliercart/addextracosts/${poPk}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || '',
            },
            body: JSON.stringify({
                shipping: shipping,
                tax: tax,
                tariff: 0
            })
        });
        const data = await response.json();

        addCostsBtn.disabled = false;

        if (data.message === 'OK') {
            result.textContent = `Added extra costs: ${data.added_lines.join(', ')}`;
            result.className = 'alert alert-block alert-success';
            result.style.display = 'block';
            // Clear inputs after success
            shippingInput.value = '';
            taxInput.value = '';
        } else {
            result.textContent = data.message || 'Failed to add extra costs';
            result.className = 'alert alert-block alert-danger';
            result.style.display = 'block';
        }
    } catch (error) {
        addCostsBtn.disabled = false;
        result.textContent = `Error: ${error.message}`;
        result.className = 'alert alert-block alert-danger';
        result.style.display = 'block';
        console.error('Add extra costs error:', error);
    }
}

/**
 * Create table showing Mouser import results
 */
function createMouserImportResultsTable(poPk, data) {
    const tableDiv = document.getElementById(`mouser-import-table-${poPk}`);
    tableDiv.innerHTML = '';

    const table = document.createElement('TABLE');
    table.classList.add('table', 'table-condensed', 'table-striped');

    // Create table head
    const thead = document.createElement('THEAD');
    const headRow = document.createElement('TR');
    ['SKU', 'Old Price', 'New Price', 'Old Qty', 'New Qty'].forEach(header => {
        const th = document.createElement('TH');
        th.textContent = header;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    // Create table body
    const tbody = document.createElement('TBODY');
    data.matched_items.forEach(item => {
        const tr = document.createElement('TR');

        // SKU
        let td = document.createElement('TD');
        td.textContent = item.SKU;
        tr.appendChild(td);

        // Old Price
        td = document.createElement('TD');
        td.textContent = `${data.currency} ${item.old_price.toFixed(4)}`;
        tr.appendChild(td);

        // New Price
        td = document.createElement('TD');
        td.textContent = `${data.currency} ${item.new_price.toFixed(4)}`;
        if (item.new_price !== item.old_price) {
            td.style.color = 'green';
            td.style.fontWeight = 'bold';
        }
        tr.appendChild(td);

        // Old Quantity
        td = document.createElement('TD');
        td.textContent = item.old_quantity || item.quantity || '';
        tr.appendChild(td);

        // New Quantity
        td = document.createElement('TD');
        td.textContent = item.new_quantity || item.quantity || '';
        if (item.new_quantity && item.old_quantity && item.new_quantity !== item.old_quantity) {
            td.style.color = 'orange';
            td.style.fontWeight = 'bold';
        }
        tr.appendChild(td);

        tbody.appendChild(tr);
    });

    // Add unmatched items with warning
    data.unmatched_items.forEach(item => {
        const tr = document.createElement('TR');
        tr.style.backgroundColor = '#fff3cd';

        let td = document.createElement('TD');
        td.textContent = item.SKU;
        tr.appendChild(td);

        td = document.createElement('TD');
        td.colSpan = 4;
        td.textContent = 'Not found in Mouser order';
        td.style.color = '#856404';
        tr.appendChild(td);

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    tableDiv.appendChild(table);
}

/**
 * Create table showing import results (Digikey)
 */
function createImportResultsTable(poPk, data) {
    const tableDiv = document.getElementById(`import-table-${poPk}`);
    tableDiv.innerHTML = '';

    const table = document.createElement('TABLE');
    table.classList.add('table', 'table-condensed', 'table-striped');

    // Create table head
    const thead = document.createElement('THEAD');
    const headRow = document.createElement('TR');
    ['SKU', 'Old Price', 'New Price', 'Old Qty', 'New Qty'].forEach(header => {
        const th = document.createElement('TH');
        th.textContent = header;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    // Create table body
    const tbody = document.createElement('TBODY');
    data.matched_items.forEach(item => {
        const tr = document.createElement('TR');

        // SKU
        let td = document.createElement('TD');
        td.textContent = item.SKU;
        tr.appendChild(td);

        // Old Price
        td = document.createElement('TD');
        td.textContent = `${data.currency} ${item.old_price.toFixed(4)}`;
        tr.appendChild(td);

        // New Price
        td = document.createElement('TD');
        td.textContent = `${data.currency} ${item.new_price.toFixed(4)}`;
        if (item.new_price !== item.old_price) {
            td.style.color = 'green';
            td.style.fontWeight = 'bold';
        }
        tr.appendChild(td);

        // Old Quantity
        td = document.createElement('TD');
        td.textContent = item.old_quantity || item.quantity || '';
        tr.appendChild(td);

        // New Quantity
        td = document.createElement('TD');
        td.textContent = item.new_quantity || item.quantity || '';
        if (item.new_quantity && item.old_quantity && item.new_quantity !== item.old_quantity) {
            td.style.color = 'orange';
            td.style.fontWeight = 'bold';
        }
        tr.appendChild(td);

        tbody.appendChild(tr);
    });

    // Add unmatched items with warning
    data.unmatched_items.forEach(item => {
        const tr = document.createElement('TR');
        tr.style.backgroundColor = '#fff3cd';

        let td = document.createElement('TD');
        td.textContent = item.SKU;
        tr.appendChild(td);

        td = document.createElement('TD');
        td.colSpan = 4;
        td.textContent = 'Not found in Digikey order';
        td.style.color = '#856404';
        tr.appendChild(td);

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    tableDiv.appendChild(table);
}

/**
 * Transfer the cart to the supplier
 */
async function transferCart(poPk, supplierName) {
    const loader = document.getElementById(`loader-${poPk}`);
    const result = document.getElementById(`result-${poPk}`);
    const cartInfo = document.getElementById(`cart-info-${poPk}`);
    const transferBtn = document.getElementById(`transfer-btn-${poPk}`);

    // Show loader, disable button
    loader.style.visibility = 'visible';
    transferBtn.disabled = true;
    result.style.display = 'none';

    try {
        // Call the backend API endpoint
        const response = await fetch(`/plugin/suppliercart/transfercart/${poPk}/`);
        const cartData = await response.json();

        // Hide loader
        loader.style.visibility = 'hidden';
        transferBtn.disabled = false;

        // Show result message
        result.textContent = cartData.message;
        result.style.display = 'block';

        if (cartData.message === 'OK') {
            result.className = 'alert alert-block alert-success';
            
            // Show cart info
            cartInfo.style.display = 'block';
            document.getElementById(`cart_key-${poPk}`).textContent = cartData.cart_key || '';
            document.getElementById(`cart_date-${poPk}`).textContent = cartData.cart_date || '';

            // Display the cart table
            if (cartData.CartItems) {
                createTable(poPk, cartData);
            }
        } else {
            result.className = 'alert alert-block alert-danger';
        }
    } catch (error) {
        loader.style.visibility = 'hidden';
        transferBtn.disabled = false;
        result.textContent = `Error: ${error.message}`;
        result.className = 'alert alert-block alert-danger';
        result.style.display = 'block';
        console.error('Transfer cart error:', error);
    }
}

/**
 * Display existing cart data
 */
function displayCartData(poPk, supplierCart) {
    const cartInfo = document.getElementById(`cart-info-${poPk}`);
    const cartKeyElem = document.getElementById(`cart_key-${poPk}`);
    const cartDateElem = document.getElementById(`cart_date-${poPk}`);

    if (supplierCart.cart) {
        cartInfo.style.display = 'block';
        cartKeyElem.textContent = supplierCart.cart.cart_key || '';
        cartDateElem.textContent = supplierCart.cart.cart_date || '';

        if (supplierCart.cart.CartItems) {
            createTable(poPk, supplierCart.cart);
        }
    }
}

/**
 * Create and populate the cart items table
 */
function createTable(poPk, cartData) {
    const tableHeadStrings = ['IPN', 'SKU', 'Required', 'Available', 'Status', 'Price', 'Total', 'Notes'];
    const tableFootStrings = ['', '', '', '', 'Total', cartData.currency_code || '', 
                              (cartData.MerchandiseTotal || 0).toFixed(4), ''];

    const myTableDiv = document.getElementById(`myDynamicTable-${poPk}`);
    myTableDiv.innerHTML = '';

    const table = document.createElement('TABLE');
    table.classList.add('table');
    table.classList.add('table-condensed');
    table.classList.add('align-right-6th-column');
    table.classList.add('align-right-7th-column');

    // Create table head
    const tableHead = document.createElement('THEAD');
    table.appendChild(tableHead);
    const headRow = document.createElement('TR');
    tableHead.appendChild(headRow);
    
    tableHeadStrings.forEach(function(item) {
        const th = document.createElement('TH');
        th.appendChild(document.createTextNode(item));
        headRow.appendChild(th);
    });

    // Create table body
    const tableBody = document.createElement('TBODY');
    table.appendChild(tableBody);

    if (cartData.CartItems && cartData.CartItems.length > 0) {
        for (let i = 0; i < cartData.CartItems.length; i++) {
            const item = cartData.CartItems[i];
            const tr = document.createElement('TR');
            tableBody.appendChild(tr);

            // IPN
            let td = document.createElement('TD');
            td.appendChild(document.createTextNode(item.IPN || ''));
            tr.appendChild(td);

            // SKU
            td = document.createElement('TD');
            td.appendChild(document.createTextNode(item.SKU || ''));
            tr.appendChild(td);

            // Required quantity
            td = document.createElement('TD');
            td.appendChild(document.createTextNode(item.QuantityRequested || '0'));
            tr.appendChild(td);

            // Available quantity
            td = document.createElement('TD');
            td.appendChild(document.createTextNode(item.QuantityAvailable || '0'));
            tr.appendChild(td);

            // Status badge
            td = document.createElement('TD');
            const statusSpan = document.createElement('SPAN');
            statusSpan.classList.add('badge');
            statusSpan.classList.add('badge-left');
            statusSpan.classList.add('rounded-pill');
            
            if ((item.QuantityRequested || 0) <= (item.QuantityAvailable || 0)) {
                statusSpan.appendChild(document.createTextNode('OK'));
                statusSpan.classList.add('bg-success');
            } else {
                statusSpan.appendChild(document.createTextNode('Not OK'));
                statusSpan.classList.add('bg-danger');
            }
            td.appendChild(statusSpan);
            tr.appendChild(td);

            // Unit price
            td = document.createElement('TD');
            td.appendChild(document.createTextNode((item.UnitPrice || 0).toFixed(4)));
            tr.appendChild(td);

            // Extended price
            td = document.createElement('TD');
            td.appendChild(document.createTextNode((item.ExtendedPrice || 0).toFixed(4)));
            tr.appendChild(td);

            // Error/Notes
            td = document.createElement('TD');
            td.appendChild(document.createTextNode(item.Error || ''));
            tr.appendChild(td);
        }
    }

    // Create table foot
    const tableFoot = document.createElement('TFOOT');
    table.appendChild(tableFoot);
    const footRow = document.createElement('TR');
    tableFoot.appendChild(footRow);

    tableFootStrings.forEach(function(item, index) {
        const tf = document.createElement('TD');
        tf.appendChild(document.createTextNode(item));
        if (index >= 4) {
            tf.style.textAlign = 'right';
            tf.style.fontWeight = 'bold';
        }
        footRow.appendChild(tf);
    });

    myTableDiv.appendChild(table);
}

