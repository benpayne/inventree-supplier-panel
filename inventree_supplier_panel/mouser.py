"""
Unfortunately Mouser does not list possible error codes. Here are some examples:

If the access key is wrong:
{'Errors': [
            {'Id': 0,
             'Code': 'Invalid',
             'Message': 'Invalid unique identifier.',
             'ResourceKey': 'InvalidIdentifier',
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': 'API Key'}
           ], 'SearchResults': None}

If the access key is empty:
{'Errors': [
            {'Id': 0,
             'Code': 'Required',
             'Message': 'Required',
             'ResourceKey': 'Required',
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': 'API Key'}
           ], 'SearchResults': None}

If there are invalid characters in the search string like non ACSII:
{'Errors': [
            {'Id': 0,
             'Code': 'InvalidCharacters',
             'Message': None,
             'ResourceKey': None,
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': None}
           ], 'SearchResults': None}

If you created more than 1000 requests within 24 hours:
{'Errors': [
            {'Id': 0,
             'Code': 'TooManyRequests',
             'Message': None,
             'ResourceKey': None,
             'ResourceFormatString': None,
             'ResourceFormatString2': None,
             'PropertyName': None}
           ], 'SearchResults': None}

"""
from common.models import InvenTreeSetting

from inventree_supplier_panel.request_wrappers import Wrappers
import re
import json


def _sanitize_api_key(text, api_key):
    """Remove API key from text to avoid exposing it in logs/UI."""
    if api_key and text:
        return text.replace(api_key, '***')
    return text


class Mouser():
    # --------------------------- get_mouser_partdata -----------------------------
    def get_mouser_partdata(self, sku, options):
        print(f"\n[MOUSER] get_mouser_partdata called:")
        print(f"  SKU: {sku}")
        print(f"  Options: {options}")

        part_data = {}
        part = {"SearchByPartRequest": {"mouserPartNumber": sku,
                                        "partSearchOptions": options,
                                        }
                }
        api_key = self.get_setting('MOUSERSEARCHKEY')
        print(f"  API Key configured: {'YES' if api_key else 'NO'}")
        
        url = 'https://api.mouser.com/api/v1.0/search/partnumber?apiKey=' + api_key
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        print(f"  Making POST request to: {url[:60]}...")
        response = Wrappers.post_request(self, json.dumps(part), url, header)
        print(f"  Response status code: {response.status_code}")
        try:
            response = response.json()
            print(f"  Response parsed as JSON successfully")
        except Exception as e:
            print(f"  ✗ Failed to parse JSON response: {e}")
            part_data['error_status'] = response
            return part_data

#        print(response)
        # If we are here, Mouser responded. Lets look for errors. Some
        # errors do not come in the Errors array, but in a Message.
        # Lets check those first
        try:
            part_data['error_status'] = response['Message']
            print(f"  ✗ Error in response Message: {response['Message']}")
            return part_data
        except Exception:
            pass

        # Then we evaluate the Errors array. there are some known errors
        # and the rest.
        if response['Errors'] != []:
            print(f"  ✗ Errors array not empty: {response['Errors']}")
            if response['Errors'][0]['Code'] == 'InvalidCharacters':
                part_data['error_status'] = 'InvalidCharacters'
            elif response['Errors'][0]['Code'] == 'Invalid':
                part_data['error_status'] = 'InvalidAuthorization'
            elif response['Errors'][0]['Code'] == 'TooManyRequests':
                part_data['error_status'] = 'TooManyRequests'
            else:
                part_data['error_status'] = response['Errors'][0]['Code']
            return part_data

        # If we came here, no errors have been reported and there sould be results.
        number_of_results = int(response['SearchResults']['NumberOfResult'])
        print(f"  Number of results from Mouser: {number_of_results}")
        if number_of_results == 0:
            print(f"  ✗ No results found")
            part_data['error_status'] = 'OK'
            part_data['number_of_results'] = number_of_results
            return part_data

        # Here least one result has been reported
        part_data['error_status'] = 'OK'
        number_of_results = 0

        # Sometimes Mouser reports parts with different SKU even when exace is set
        # Lest filter those
        print(f"  Filtering results for exact SKU match...")
        for pd in response['SearchResults']['Parts']:
            print(f"    Checking part: {pd.get('MouserPartNumber')} vs requested: {sku}")
            if pd['MouserPartNumber'] == sku:
                print(f"    ✓ Exact match found!")
                part_data['price_breaks'] = []
                part_data['SKU'] = pd['MouserPartNumber']
                part_data['MPN'] = pd['ManufacturerPartNumber']
                part_data['URL'] = pd['ProductDetailUrl']
                part_data['lifecycle_status'] = pd['LifecycleStatus']
                part_data['pack_quantity'] = pd['Mult']
                part_data['description'] = pd['Description']
                part_data['package'] = Mouser.get_mouser_package(self, pd)
                for pb in pd['PriceBreaks']:
                    new_price = Mouser.reformat_mouser_price(self, pb['Price'])
                    part_data['price_breaks'].append({'Quantity': pb['Quantity'], 'Price': new_price, 'Currency': pb['Currency']})
                number_of_results = number_of_results + 1
            else:
                print(f"    ✗ SKU does not match, skipping")
        part_data['number_of_results'] = number_of_results
        print(f"  Final number of matching results: {number_of_results}")
        return part_data

    # --------------------------- get_mouser_partdata_extended -----------------------------
    # Extended version that returns additional fields for full part import
    def get_mouser_partdata_extended(self, sku, options):
        """
        Get extended part data from Mouser API including manufacturer, category, images, attributes.
        This is used for full part import functionality.
        """
        print(f"\n[MOUSER-EXTENDED] get_mouser_partdata_extended called:")
        print(f"  SKU: {sku}")
        
        part_data = {}
        part = {"SearchByPartRequest": {"mouserPartNumber": sku,
                                        "partSearchOptions": options,
                                        }
                }
        api_key = self.get_setting('MOUSERSEARCHKEY')
        
        url = 'https://api.mouser.com/api/v1.0/search/partnumber?apiKey=' + api_key
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response = Wrappers.post_request(self, json.dumps(part), url, header)
        
        try:
            response = response.json()
        except Exception as e:
            print(f"  ✗ Failed to parse JSON response: {e}")
            part_data['error_status'] = str(e)
            return part_data

        # Check for errors
        try:
            part_data['error_status'] = response['Message']
            return part_data
        except Exception:
            pass

        if response['Errors'] != []:
            if response['Errors'][0]['Code'] == 'InvalidCharacters':
                part_data['error_status'] = 'InvalidCharacters'
            elif response['Errors'][0]['Code'] == 'Invalid':
                part_data['error_status'] = 'InvalidAuthorization'
            elif response['Errors'][0]['Code'] == 'TooManyRequests':
                part_data['error_status'] = 'TooManyRequests'
            else:
                part_data['error_status'] = response['Errors'][0]['Code']
            return part_data

        # Check for results
        number_of_results = int(response['SearchResults']['NumberOfResult'])
        if number_of_results == 0:
            part_data['error_status'] = 'OK'
            part_data['number_of_results'] = number_of_results
            return part_data

        # Find exact match
        pd = None
        for part_result in response['SearchResults']['Parts']:
            if part_result['MouserPartNumber'] == sku:
                pd = part_result
                break
        
        if not pd:
            part_data['error_status'] = 'OK'
            part_data['number_of_results'] = 0
            return part_data

        # Extract basic data
        part_data['SKU'] = pd['MouserPartNumber']
        part_data['MPN'] = pd['ManufacturerPartNumber']
        part_data['URL'] = pd['ProductDetailUrl']
        part_data['lifecycle_status'] = pd['LifecycleStatus']
        part_data['pack_quantity'] = pd['Mult']
        part_data['description'] = pd['Description']
        part_data['package'] = Mouser.get_mouser_package(self, pd)

        # Extract manufacturer name
        try:
            part_data['manufacturer_name'] = pd.get('Manufacturer', '')
            print(f"  Manufacturer: {part_data['manufacturer_name']}")
        except (KeyError, TypeError):
            part_data['manufacturer_name'] = None

        # Extract category
        try:
            part_data['category'] = pd.get('Category', '')
            print(f"  Category: {part_data['category']}")
        except (KeyError, TypeError):
            part_data['category'] = ''

        # Extract image URL
        try:
            part_data['image_url'] = pd.get('ImagePath', '')
            print(f"  Image URL: {part_data['image_url'][:60]}..." if part_data['image_url'] else "  No image available")
        except (KeyError, TypeError):
            part_data['image_url'] = None

        # Extract data sheet URL
        try:
            part_data['data_sheet_url'] = pd.get('DataSheetUrl', '')
        except (KeyError, TypeError):
            part_data['data_sheet_url'] = ''

        # Extract product attributes
        try:
            part_data['attributes'] = []
            if 'ProductAttributes' in pd:
                for attr in pd['ProductAttributes']:
                    part_data['attributes'].append({
                        'name': attr.get('AttributeName', ''),
                        'value': attr.get('AttributeValue', '')
                    })
            print(f"  Attributes: {len(part_data['attributes'])} found")
        except (KeyError, TypeError):
            part_data['attributes'] = []

        # Price breaks
        part_data['price_breaks'] = []
        for pb in pd['PriceBreaks']:
            new_price = Mouser.reformat_mouser_price(self, pb['Price'])
            part_data['price_breaks'].append({
                'Quantity': pb['Quantity'],
                'Price': new_price,
                'Currency': pb['Currency']
            })

        part_data['error_status'] = 'OK'
        part_data['number_of_results'] = 1
        print(f"  ✓ Extended part data extracted successfully")
        return part_data

    # ------------------------------- get_mouser_package --------------------------
    # Extracts the available packages from the Mouser part data json. The language
    # the Mouser uses for the anwser cannot be set. It seems to be fixed toe the region
    # where the request comes from. There is a setting for this with two values so far.
    def get_mouser_package(self, part_data):

        att_names = {'packaging': {'German': 'Verpackung', 'English': 'Packaging'}}
        package = ''
        try:
            attributes = part_data['ProductAttributes']
        except Exception:
            return None
        for att in attributes:
            if att['AttributeName'] == att_names['packaging'][self.get_setting('MOUSERLANGUAGE')]:
                package = package + att['AttributeValue'] + ', '
        return (package)

    # --------------------------- reformat_mouser_price --------------------------
    # We need a Mouser specific modification to the price answer because they put
    # funny things inside like an EURO sign and they use , instead of .

    def reformat_mouser_price(self, price):
        price = price.replace('.', '')
        price = price.replace(',', '.')
        non_decimal = re.compile(r'[^\d.]+')
        price = non_decimal.sub('', price)
        if price == '':
            price = 0
        else:
            price = float(price)
        return price

    # ------------------------ create_cart -------------------------------------------
    # For Mouser this is just a dummy. We do not create a cart ID so far. It is
    # automatically created by Mouser during item insertion. The return values are
    # only for error handling.

    def create_mouser_cart(self, order):
        cart_data = {}
        cart_data['ID'] = ''
        cart_data['error_status'] = 'OK'
        return (cart_data)

    # ------------------------ update_cart ----------------------------------
    # Actually we send an empty CartKey. So Mouser creates a new key each time
    # the button is pressed. This should be improved in future. It is mandatory
    # to send a county code. The code is dreived from the Inventree currency setting.
    # This might not always fit.

    def update_mouser_cart(self, order, cart_key):
        country_code = self.COUNTRY_CODES[InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')]
        cart_items = []
        shopping_cart = {}

        for item in order.lines.all():
            cart_items.append({'MouserPartNumber': item.part.SKU,
                               'Quantity': int(item.quantity),
                               'CustomerPartNumber': item.part.part.IPN
                               })
        cart = {
            "CartKey": cart_key,
            "CartItems": cart_items
        }
        url = 'https://api.mouser.com/api/v001/cart/items/insert?apiKey=' + self.get_setting('MOUSERCARTKEY') + '&countryCode=' + country_code
        header = {'Content-type': 'application/json', 'Accept': 'application/json'}
        response = Wrappers.post_request(self, json.dumps(cart), url, header)

        # Return with error if response was not OK
        if response.status_code != 200:
            shopping_cart['error_status'] = str(response.content)
            return (shopping_cart)
        response = response.json()
        if response['Errors'] != []:
            shopping_cart['error_status'] = response['Errors'][0]['Message']
            return (shopping_cart)
        cart_items = []
        for p in response['CartItems']:
            if p['Errors'] == []:
                cart_items.append({'SKU': p['MouserPartNumber'],
                                   'IPN': p['CartItemCustPartNumber'],
                                   'Manufacturer': p['Manufacturer'],
                                   'MPN': p['MfrPartNumber'],
                                   'Description': p['Description'],
                                   'QuantityRequested': p['Quantity'],
                                   'QuantityAvailable': p['MouserATS'],
                                   'UnitPrice': p['UnitPrice'],
                                   'ExtendedPrice': p['ExtendedPrice'],
                                   'Error': p['PackagingChoice']
                                   })
            else:
                cart_items.append({'SKU': p['MouserPartNumber'],
                                   'IPN': p['CartItemCustPartNumber'],
                                   'QuantityRequested': p['Quantity'],
                                   'QuantityAvailable': p['MouserATS'],
                                   'UnitPrice': p['UnitPrice'],
                                   'ExtendedPrice': p['ExtendedPrice'],
                                   'Error': p['Errors'][0]['Message']
                                   })

        # Here we get the currency_code from the Mouser response
        shopping_cart = {'MerchandiseTotal': response['MerchandiseTotal'],
                         'CartItems': cart_items,
                         'cart_key': response['CartKey'],
                         'currency_code': response['CurrencyCode'],
                         'error_status': 'OK',
                         }
        return (shopping_cart)

    # -------------------- Order Import Functions --------------------
    # These functions retrieve order data from Mouser to import actual
    # prices and order numbers back into InvenTree POs.

    def get_mouser_order_history(self, days_back=90):
        """
        Get recent Mouser orders from Order History API.
        Returns a list of orders with order_number, date, and web_order_id.
        """
        from datetime import datetime, timedelta

        print(f"\n[MOUSER] Getting order history for last {days_back} days...")

        api_key = self.get_setting('MOUSERORDERKEY')
        if not api_key:
            print("[MOUSER] ✗ MOUSERORDERKEY not configured")
            return {'error_status': 'MOUSERORDERKEY not configured', 'orders': []}

        # Calculate date range in mm/dd/yyyy format (Mouser's required format)
        end_date = datetime.now().strftime('%m/%d/%Y')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')

        # Mouser Order History API uses GET requests with query parameters
        # Endpoints from https://api.mouser.com/api/docs/V1:
        # - /api/v1/orderhistory/ByDateFilter?apiKey=...&dateFilter=ThisMonth
        # - /api/v1/orderhistory/ByDateRange?apiKey=...&startDate=mm/dd/yyyy&endDate=mm/dd/yyyy
        endpoints_to_try = [
            f'https://api.mouser.com/api/v1/orderhistory/ByDateRange?apiKey={api_key}&startDate={start_date}&endDate={end_date}',
            f'https://api.mouser.com/api/v1.0/orderhistory/ByDateRange?apiKey={api_key}&startDate={start_date}&endDate={end_date}',
            f'https://api.mouser.com/api/v1/orderhistory/ByDateFilter?apiKey={api_key}&dateFilter=LastQuarter',
        ]

        header = {'Accept': 'application/json'}

        print(f"[MOUSER] Fetching orders from {start_date} to {end_date}")

        response = None
        for url in endpoints_to_try:
            # Sanitize URL for logging (hide API key)
            url_safe = url.replace(api_key, '***') if api_key else url
            print(f"[MOUSER] Trying GET {url_safe}")
            response = Wrappers.get_request(self, url, headers=header)

            print(f"[MOUSER] Response status: {response.status_code}")
            if response.status_code == 200:
                break
            print(f"[MOUSER] Response: {_sanitize_api_key(response.text[:200], api_key)}")

        if response is None:
            return {'error_status': 'No endpoints worked', 'orders': []}

        if response.status_code != 200:
            print(f"[MOUSER] ✗ Order history request failed: {response.status_code}")
            # Return a user-friendly error without exposing API details
            return {'error_status': 'Order history not available - please enter Web Order # manually', 'orders': []}

        try:
            response_data = response.json()
            print(f"[MOUSER] Response data type: {type(response_data)}")
            print(f"[MOUSER] Response data: {_sanitize_api_key(str(response_data)[:500], api_key)}")
        except Exception as e:
            print(f"[MOUSER] ✗ Failed to parse response: {e}")
            print(f"[MOUSER] Raw response: {_sanitize_api_key(response.text[:500], api_key)}")
            return {'error_status': 'Failed to parse order history response', 'orders': []}

        # Check for errors in response
        if isinstance(response_data, dict) and response_data.get('Errors'):
            error_msg = response_data['Errors'][0].get('Message', 'Unknown error')
            print(f"[MOUSER] ✗ API error: {error_msg}")
            return {'error_status': error_msg, 'orders': []}

        # Parse the order list - format may vary based on actual API response
        orders = []
        order_list = response_data.get('OrderHistoryItems') or response_data.get('Orders') or response_data
        if isinstance(order_list, list):
            for order in order_list:
                orders.append({
                    'order_number': order.get('OrderNumber') or order.get('SalesOrderNumber') or order.get('WebOrderNumber'),
                    'date_entered': order.get('OrderDate') or order.get('DateEntered') or order.get('CreatedDate'),
                    'web_order_id': order.get('WebOrderNumber') or order.get('WebOrderId'),
                    'po_number': order.get('PONumber') or order.get('CustomerPO', '')
                })

        print(f"[MOUSER] ✓ Found {len(orders)} orders")
        return {'error_status': 'OK', 'orders': orders}

    def get_mouser_order_details(self, order_number):
        """
        Get detailed order information including line items with actual prices.
        """
        print(f"\n[MOUSER] Getting order details for order {order_number}...")

        api_key = self.get_setting('MOUSERORDERKEY')
        if not api_key:
            print("[MOUSER] ✗ MOUSERORDERKEY not configured")
            return {'error_status': 'MOUSERORDERKEY not configured'}

        # Try GET request for order details using the correct endpoint
        # From Mouser API docs: /api/v1/orderhistory/webOrderNumber?apiKey=...&webOrderNumber=...
        url = f'https://api.mouser.com/api/v1/orderhistory/webOrderNumber?apiKey={api_key}&webOrderNumber={order_number}'
        header = {'Accept': 'application/json'}

        print(f"[MOUSER] Fetching order {order_number}")
        response = Wrappers.get_request(self, url, headers=header)

        print(f"[MOUSER] Response status: {response.status_code}")
        if response.status_code != 200:
            # Try alternative endpoint - the /order/ endpoint (used for cart-created orders)
            print(f"[MOUSER] Trying /order/ endpoint...")
            url_alt = f'https://api.mouser.com/api/v1/order/{order_number}?apiKey={api_key}'
            response = Wrappers.get_request(self, url_alt, headers=header)
            print(f"[MOUSER] Alt response status: {response.status_code}")

        if response.status_code != 200:
            print(f"[MOUSER] ✗ Order details request failed: {response.status_code}")
            return {'error_status': f'Order not found (error {response.status_code})'}

        try:
            order_data = response.json()
            print(f"[MOUSER] Order response keys: {order_data.keys() if isinstance(order_data, dict) else 'list'}")
        except Exception as e:
            print(f"[MOUSER] ✗ Failed to parse response: {e}")
            return {'error_status': 'Failed to parse order response'}

        # Check for errors
        if isinstance(order_data, dict) and order_data.get('Errors'):
            error_msg = order_data['Errors'][0].get('Message', 'Unknown error')
            print(f"[MOUSER] ✗ API error: {error_msg}")
            return {'error_status': error_msg}

        # Parse the order details - using actual Mouser API field names
        # Web Order # is what user enters, Sales Order # (OrderID) is Mouser's internal ID
        result = {
            'error_status': 'OK',
            'order_number': order_number,  # This is the Web Order # the user entered
            'sales_order_id': order_data.get('OrderID') or order_data.get('SalesOrderNumber', ''),  # Mouser's Sales Order #
            'web_order_id': order_number,  # Same as order_number for clarity
            'po_number': order_data.get('PONumber') or order_data.get('CustomerPO', ''),
            'currency': order_data.get('CurrencyCode') or order_data.get('Currency', 'USD'),
            'shipping_cost': float(order_data.get('additionalFeesTotal') or order_data.get('ShippingCost') or 0),
            'tax': float(order_data.get('TaxAmount') or order_data.get('Tax') or 0),
            'merchandise_total': float(order_data.get('MerchandiseTotal') or order_data.get('Subtotal') or 0),
            'order_total': float(order_data.get('OrderTotal') or order_data.get('Total') or 0),
            'line_items': []
        }

        # Parse line items
        raw_items = order_data.get('OrderLines') or order_data.get('LineItems') or order_data.get('Items', [])
        for item in raw_items:
            result['line_items'].append({
                'mouser_part_number': item.get('MouserPartNumber') or item.get('PartNumber', ''),
                'manufacturer_part_number': item.get('MfrPartNumber') or item.get('ManufacturerPartNumber', ''),
                'manufacturer': item.get('Manufacturer', ''),
                'description': item.get('Description', ''),
                'quantity': int(item.get('Quantity') or item.get('QuantityOrdered', 0)),
                'unit_price': float(item.get('UnitPrice') or item.get('Price', 0)),
                'extended_price': float(item.get('ExtendedPrice') or item.get('LineTotal', 0)),
                'customer_part_number': item.get('CustomerPartNumber') or item.get('CustPartNumber', '')
            })

        print(f"[MOUSER] ✓ Order {order_number} has {len(result['line_items'])} line items")
        print(f"[MOUSER] Extra costs - Shipping: ${result['shipping_cost']}, Tax: ${result['tax']}")

        return result
