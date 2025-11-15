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
        </div>
    `;

    // Set up the transfer button click handler
    const transferBtn = target.querySelector(`#transfer-btn-${poPk}`);
    transferBtn.addEventListener('click', () => transferCart(poPk, supplierName));

    // Load existing cart data if available from PO metadata
    if (data.instance?.metadata?.SupplierCart) {
        displayCartData(poPk, data.instance.metadata.SupplierCart);
    }
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

