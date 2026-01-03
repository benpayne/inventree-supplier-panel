from common.models import InvenTreeSetting

from inventree_supplier_panel.request_wrappers import Wrappers
from inventree_supplier_panel.meta_access import MetaAccess
from urllib.parse import quote
import json


class Digikey():

    # --------------------------- get_digikey_partdata ----------------------------
    # This part is for the new digikey search V4. In case of problems, the V3
    # version is still available below. It can be selected by changing the
    # function selector in the main file.

    def get_digikey_partdata_v4(self, sku, options):
        print(f"\n[DIGIKEY] get_digikey_partdata_v4 called:")
        print(f"  SKU: {sku}")
        print(f"  Options: {options}")
        
        part_data = {}
        print(f"  Refreshing Digikey access token...")
        token = Digikey.refresh_digikey_access_token(self)
        if token['status_code'] != 200:
            print(f"  ✗ Token refresh failed: {token['message']}")
            part_data['error_status'] = token['message']
            return part_data
        print(f"  ✓ Token refreshed successfully")

        # replace invalid characters in the partnumber
        sku = quote(sku, safe='')
        url = f'https://api.digikey.com/products/v4/search/{sku}/productdetails'
        country_code = self.COUNTRY_CODES[InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')]
        print(f"  Country code: {country_code}")
        print(f"  Making GET request to: {url}")
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'Content-Type': 'application/json',
            'X-DIGIKEY-Locale-Currency': InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY'),
            'X-DIGIKEY-Locale-Site': country_code,
            'X-DIGIKEY-Locale-Language': 'EN'
        }
        response = Wrappers.get_request(self, url, headers=header)
        print(f"  Response status code: {response.status_code}")
        try:
            response_json = response.json()
            print(f"  Response parsed as JSON successfully")
        except Exception as e:
            print(f"  ✗ Failed to parse JSON response: {e}")
            part_data['error_status'] = response
            return part_data

        # If we are here, digikey responded. Lets look for errors.
        try:
            if response_json['status'] != 200:
                error_msg = response_json['title'] + response_json['detail']
                print(f"  ✗ Error in response: {error_msg}")
                part_data['error_status'] = error_msg
                return part_data
        except Exception:
            pass
        print('  Remaining requests:', response.headers.get('X-RateLimit-Remaining', 'unknown'))

        # Select the right variation that fits the searched SKU
        print(f"  Searching for matching product variation...")
        for product in response_json['Product']['ProductVariations']:
            print(f"    Checking: {product['DigiKeyProductNumber']} vs requested: {sku}")
            if product['DigiKeyProductNumber'] == sku:
                print(f"    ✓ Exact match found!")
                break
        else:
            print(f"  ✗ No matching product variation found for SKU: {sku}")
            part_data['error_status'] = f'No matching product variation for {sku}'
            part_data['number_of_results'] = 0
            return part_data
        part_data['SKU'] = product['DigiKeyProductNumber']
        part_data['MPN'] = response_json['Product']['ManufacturerProductNumber']
        part_data['URL'] = response_json['Product']['ProductUrl']
        part_data['lifecycle_status'] = response_json['Product']['ProductStatus']['Status']
        part_data['description'] = response_json['Product']['Description']['DetailedDescription']
        part_data['package'] = product['PackageType']['Name']
        part_data['price_breaks'] = []
        part_data['error_status'] = 'OK'
        part_data['number_of_results'] = 1
        print(f"  ✓ Part data extracted successfully")

        # Digikey responds 0 for the pack quantity on obsolete parts. We change this because
        # Inventree does not support 0 here.
        if product['MinimumOrderQuantity'] == 0:
            part_data['pack_quantity'] = '1'
        else:
            part_data['pack_quantity'] = str(product['MinimumOrderQuantity'])
        for pb in product['StandardPricing']:
            part_data['price_breaks'].append({'Quantity': pb['BreakQuantity'],
                                              'Price': pb['UnitPrice'],
                                              'Currency': response_json['SearchLocaleUsed']['Currency']
                                              })
        print(f"  Found {len(part_data['price_breaks'])} price breaks")
        return (part_data)

    # --------------------------- get_digikey_partdata_extended ----------------------------
    # Extended version that returns additional fields for full part import
    def get_digikey_partdata_extended(self, sku, options):
        """
        Get extended part data from Digikey API including manufacturer, category, images, parameters.
        This is used for full part import functionality.
        """
        print(f"\n[DIGIKEY-EXTENDED] get_digikey_partdata_extended called:")
        print(f"  SKU: {sku}")
        
        part_data = {}
        print(f"  Refreshing Digikey access token...")
        token = Digikey.refresh_digikey_access_token(self)
        if token['status_code'] != 200:
            print(f"  ✗ Token refresh failed: {token['message']}")
            part_data['error_status'] = token['message']
            return part_data
        print(f"  ✓ Token refreshed successfully")

        # replace invalid characters in the partnumber
        sku = quote(sku, safe='')
        url = f'https://api.digikey.com/products/v4/search/{sku}/productdetails'
        country_code = self.COUNTRY_CODES[InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')]
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'Content-Type': 'application/json',
            'X-DIGIKEY-Locale-Currency': InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY'),
            'X-DIGIKEY-Locale-Site': country_code,
            'X-DIGIKEY-Locale-Language': 'EN'
        }
        response = Wrappers.get_request(self, url, headers=header)
        print(f"  Response status code: {response.status_code}")
        
        try:
            response_json = response.json()
        except Exception as e:
            print(f"  ✗ Failed to parse JSON response: {e}")
            part_data['error_status'] = str(e)
            return part_data

        # Check for errors
        try:
            if response_json.get('status') and response_json['status'] != 200:
                error_msg = response_json.get('title', '') + ' ' + response_json.get('detail', '')
                print(f"  ✗ Error in response: {error_msg}")
                part_data['error_status'] = error_msg
                return part_data
        except Exception:
            pass

        # Select the right variation
        product = None
        for prod in response_json['Product']['ProductVariations']:
            if prod['DigiKeyProductNumber'] == sku:
                product = prod
                break
        
        if not product:
            print(f"  ✗ No matching product variation found")
            part_data['error_status'] = f'No matching product variation for {sku}'
            return part_data

        # Extract basic data
        part_data['SKU'] = product['DigiKeyProductNumber']
        part_data['MPN'] = response_json['Product']['ManufacturerProductNumber']
        part_data['URL'] = response_json['Product']['ProductUrl']
        part_data['lifecycle_status'] = response_json['Product']['ProductStatus']['Status']
        part_data['description'] = response_json['Product']['Description']['DetailedDescription']
        part_data['package'] = product['PackageType']['Name']
        
        # Extract manufacturer name
        try:
            part_data['manufacturer_name'] = response_json['Product']['Manufacturer']['Name']
            print(f"  Manufacturer: {part_data['manufacturer_name']}")
        except (KeyError, TypeError):
            part_data['manufacturer_name'] = None
            print(f"  ✗ Could not extract manufacturer name")

        # Extract category
        try:
            # Try taxonomy first, then category
            if 'LimitedTaxonomy' in response_json['Product']:
                part_data['category'] = response_json['Product']['LimitedTaxonomy'].get('Value', '')
            elif 'Category' in response_json['Product']:
                part_data['category'] = response_json['Product']['Category'].get('Name', '')
            else:
                part_data['category'] = ''
            print(f"  Category: {part_data['category']}")
        except (KeyError, TypeError):
            part_data['category'] = ''

        # Extract primary photo
        try:
            part_data['primary_photo'] = response_json['Product'].get('PrimaryPhoto', '')
            print(f"  Primary Photo: {part_data['primary_photo'][:60]}..." if part_data['primary_photo'] else "  No photo available")
        except (KeyError, TypeError):
            part_data['primary_photo'] = None

        # Extract parameters
        try:
            part_data['parameters'] = []
            if 'Parameters' in response_json['Product']:
                for param in response_json['Product']['Parameters']:
                    part_data['parameters'].append({
                        'name': param.get('Parameter', ''),
                        'value': param.get('Value', '')
                    })
            print(f"  Parameters: {len(part_data['parameters'])} found")
        except (KeyError, TypeError):
            part_data['parameters'] = []

        # Extract HTSUS code
        try:
            part_data['htsus'] = response_json['Product'].get('HtsusCode', '')
        except (KeyError, TypeError):
            part_data['htsus'] = ''

        # Pack quantity
        if product['MinimumOrderQuantity'] == 0:
            part_data['pack_quantity'] = '1'
        else:
            part_data['pack_quantity'] = str(product['MinimumOrderQuantity'])

        # Price breaks
        part_data['price_breaks'] = []
        for pb in product['StandardPricing']:
            part_data['price_breaks'].append({
                'Quantity': pb['BreakQuantity'],
                'Price': pb['UnitPrice'],
                'Currency': response_json['SearchLocaleUsed']['Currency']
            })

        part_data['error_status'] = 'OK'
        part_data['number_of_results'] = 1
        print(f"  ✓ Extended part data extracted successfully")
        return part_data

    # ------------------- create_digikey_cart
    # Digikey does not have a cart API. So we create a list using the MyLists API
    # The list can easily be converted to a shopping cart or a quote in the
    # WEB UI of Digikey. However the List API is not so simple to handle because
    # all the list names are stored and blocked for future use. Even deleted ones..

    def create_digikey_cart(self, order):
        cart_data = {}
        from datetime import datetime
        print(f"\n[DIGIKEY] Starting list creation for PO: {order.reference}")
        list_name = MetaAccess.get_value(self, order, 'DigiKeyListName')
        print(f"[DIGIKEY] Existing list name from metadata: {list_name}")
        if list_name is None:
            # Use timestamp for more uniqueness
            timestamp = datetime.now().strftime('%y%m%d-%H%M%S')
            list_name = f"{order.reference}-{timestamp}"
            print(f"[DIGIKEY] Generated new list name: {list_name}")
        else:
            # Extract base and increment version
            parts = list_name.rsplit('-', 1)
            if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 2:
                version = int(parts[1]) + 1
                list_name = f"{parts[0]}-{str(version).zfill(2)}"
                print(f"[DIGIKEY] Incremented version to: {list_name}")
            else:
                # Fallback: append timestamp
                timestamp = datetime.now().strftime('%y%m%d-%H%M%S')
                list_name = f"{order.reference}-{timestamp}"
                print(f"[DIGIKEY] Generated new timestamp list name: {list_name}")
        
        print(f"[DIGIKEY] Refreshing access token...")
        token = Digikey.refresh_digikey_access_token(self)

        if token['status_code'] != 200:
            print(f"[DIGIKEY] ✗ Token refresh failed: {token['message']}")
            cart_data['error_status'] = token['message']
            return cart_data
        
        # Try to find a valid unique name
        print(f"[DIGIKEY] Checking if list name '{list_name}' is available...")
        i = 0
        original_list_name = list_name
        while not Digikey.check_valid_listname(self, list_name):
            i = i + 1
            list_name = f"{original_list_name}-{str(i).zfill(2)}"
            print(f"[DIGIKEY] List name taken, trying: {list_name} (attempt {i}/20)")
            if i >= 20:
                print(f"[DIGIKEY] ✗ Failed to find valid list name after 20 attempts")
                cart_data['ID'] = ''
                cart_data['error_status'] = 'No valid list name found within 20 attempts'
                return cart_data
        print(f"[DIGIKEY] ✓ List name '{list_name}' is available")
        MetaAccess.set_value(self, order, 'DigiKeyListName', list_name)
        url = 'https://api.digikey.com/mylists/v1/lists'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'Content-Type': 'application/json'
        }
        url_data = {
            'ListName': list_name,
            'accept': 'application/json'
        }
        response = Wrappers.post_request(self, json.dumps(url_data), url, headers=header)
        
        # Check if the request was successful
        if response.status_code not in [200, 201]:
            cart_data['ID'] = ''
            cart_data['error_status'] = f'Failed to create list: {response.status_code} - {response.text}'
            print(f"[DIGIKEY] ✗ List creation failed: {response.status_code} - {response.text}")
            return cart_data
        
        # Extract the list ID from the response
        response_data = response.json()
        print(f"[DIGIKEY] Raw API response: {response_data}")
        
        # The Digikey API can return either a string ID or an object with ListId
        if isinstance(response_data, str):
            # Response is just the ListId string
            cart_data['ID'] = response_data
        elif isinstance(response_data, dict):
            # Response is an object, extract ListId
            cart_data['ID'] = response_data.get('ListId', response_data)
        else:
            # Unexpected response format
            cart_data['ID'] = str(response_data)
        
        cart_data['error_status'] = 'OK'
        print(f"[DIGIKEY] ✓ Created Digikey list: {list_name} with ID: {cart_data['ID']}")
        return (cart_data)

    # Check if list name is available - now with error checking!
    def check_valid_listname(self, list_name):
        url = f'https://api.digikey.com/mylists/v1/lists/validate/{list_name}?createdBy=xxxx'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept': 'application/json'
        }
        response = Wrappers.get_request(self, url, headers=header)
        
        # Check if the API call was successful
        if response.status_code != 200:
            print(f"[DIGIKEY] ✗ Error checking list name: {response.status_code} - {response.text}")
            # If API call fails, we can't validate, so assume name is taken to be safe
            return False
        
        is_valid = (response.content == b'true')
        print(f"[DIGIKEY] List name '{list_name}' validation result: {is_valid} (response: {response.content})")
        return is_valid

    # ------------------------------------------------------------------
    # Digikey has no shopping cart API. So we create a list using the MyLists API.
    # The list can easily be transferred into an order in the web interface.

    def update_digikey_cart(self, order, list_id):

        pack_types = {'TR': 'full reel', 'DKR': 'DigiReel', 'CT': 'cut tape', 'BAG': 'bulk'}
        url = f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts'
        header = {'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
                  'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
                  'accept': 'application/json',
                  'Content-Type': 'application/json'
                  }
        cart_items = []
        for item in order.lines.all():
            cart_items.append({'RequestedPartNumber': item.part.SKU,
                               'Quantities': [{'Quantity': int(item.quantity)}],
                               'CustomerReference': item.part.part.IPN
                               })
        # The post equest just generates the list in the Digikey cloud
        Wrappers.post_request(self, json.dumps(cart_items), url, header)

        # Now we get the parts from the generated list
        parts_in_list = Digikey.get_parts_in_list(self, list_id)
        cart_items = []
        merchandise_total = 0
        for p in parts_in_list['PartsList']:
            if p['DigiKeyPartNumber'] != '':

                # For an obsolete part PackOptions is empty. We set a default for the rest
                # not to crash
                pack_option = {}
                pack_option['CalculatedUnitPrice'] = 0
                pack_option['ExtendedPrice'] = 0
                pack_option['MinimumOrderQuantity'] = 1
                pack_option['PackType'] = 'Obsolete'
                for pack_option in p['Quantities'][0]['PackOptions']:
                    if pack_option['DigiKeyPartNumber'] == p['DigiKeyPartNumber']:
                        break
                if pack_option['MinimumOrderQuantity'] > p['Quantities'][0]['QuantityRequested']:
                    cart_items.append({'SKU': p['DigiKeyPartNumber'],
                                       'IPN': p['CustomerReference'],
                                       'MPN': '',
                                       'Manufacturer': '',
                                       'Description': '',
                                       'QuantityRequested': p['Quantities'][0]['QuantityRequested'],
                                       'QuantityAvailable': p['QuantityAvailable'],
                                       'UnitPrice': 0,
                                       'ExtendedPrice': 0,
                                       'Error': 'Minimum order quantity not reached',
                                       })
                else:
                    try:
                        pack = pack_types[pack_option['PackType']]
                    except Exception:
                        pack = pack_option['PackType']
                    cart_items.append({'SKU': p['DigiKeyPartNumber'],
                                       'IPN': p['CustomerReference'],
                                       'MPN': p['ManufacturerPartNumber'],
                                       'Manufacturer': p['Manufacturer'],
                                       'Description': p['Description'],
                                       'QuantityRequested': p['Quantities'][0]['QuantityRequested'],
                                       'QuantityAvailable': p['QuantityAvailable'],
                                       'UnitPrice': pack_option['CalculatedUnitPrice'],
                                       'ExtendedPrice': pack_option['ExtendedPrice'],
                                       'Error': pack,
                                       })
                    merchandise_total = merchandise_total + pack_option['ExtendedPrice']
            else:
                cart_items.append({'SKU': p['RequestedPartNumber'],
                                   'IPN': p['CustomerReference'],
                                   'MPN': '',
                                   'Manufacturer': '',
                                   'Description': '',
                                   'QuantityRequested': p['Quantities'][0]['QuantityRequested'],
                                   'QuantityAvailable': p['QuantityAvailable'],
                                   'UnitPrice': 0,
                                   'ExtendedPrice': 0,
                                   'Error': 'Partnumber not found at Digikey',
                                   })

        # Digikey does not return a currency code. So we take the one from the settings.
        shopping_cart = {'MerchandiseTotal': merchandise_total,
                         'CartItems': cart_items,
                         'cart_key': MetaAccess.get_value(self, order, 'DigiKeyListName'),
                         'currency_code': InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY'),
                         }
        shopping_cart['error_status'] = 'OK'
        return (shopping_cart)

    # ------------------------------- get_parts_in_list ----------------------
    def get_parts_in_list(self, list_id):
        currency_code = InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY')
        country_code = self.COUNTRY_CODES[currency_code]
        url = f'https://api.digikey.com/mylists/v1/lists/{list_id}/parts/?countryIso={country_code}&currencyIso={currency_code}&languageIso={country_code}&createdBy=xxxx&pricingCountryIso={country_code}'
        header = {
            'Authorization': f"{'Bearer'} {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept': 'application/json'
        }
        response = Wrappers.get_request(self, url, headers=header)
        if not response:
            return (None)
        return (response.json())

    # -------------------- Here starts the digikey token stuff --------------------
    def refresh_digikey_access_token(self):

        url = 'https://api.digikey.com/v1/oauth2/token'
        client_id = self.get_setting('DIGIKEY_CLIENT_ID')
        client_secret = self.get_setting('DIGIKEY_CLIENT_SECRET')
        refresh_token = self.get_setting('DIGIKEY_REFRESH_TOKEN')
        url_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        header = {}
        token = {}
        response = Wrappers.post_request(self, url_data, url, headers=header)
        response_json = response.json()

        # On success there is no StatusCode, just in error case
        try:
            token['status_code'] = response_json['StatusCode']
            token['message'] = response_json['ErrorDetails']
            return (token)
        except Exception:
            pass
        print('\033[32mToken refresh SUCCESS\033[0m')
        response_data = response.json()
        self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
        self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
        token['status_code'] = response.status_code
        token['message'] = 'success'
        token['acces_token'] = response_data['access_token']
        token['refresh_token'] = response_data['refresh_token']
        return (token)

    # -------------------- Order Import Functions --------------------
    # These functions retrieve order data from Digikey to import actual
    # prices and order numbers back into InvenTree POs.

    def get_digikey_order_history(self, days_back=30):
        """
        Get recent Digikey orders from the Order History API.
        Returns a list of orders with salesorder_id, date, and PO reference.
        """
        from datetime import datetime, timedelta

        print(f"\n[DIGIKEY] Getting order history for last {days_back} days...")

        # Refresh token first
        token = Digikey.refresh_digikey_access_token(self)
        if token['status_code'] != 200:
            print(f"[DIGIKEY] ✗ Token refresh failed: {token['message']}")
            return {'error_status': token['message'], 'orders': []}

        # Calculate date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Use /History endpoint with capitalized query params (per Digikey API spec)
        url = f'https://api.digikey.com/OrderDetails/v3/History?StartDate={start_date}&EndDate={end_date}'
        header = {
            'Authorization': f"Bearer {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept': 'application/json'
        }

        print(f"[DIGIKEY] Fetching orders from {start_date} to {end_date}")
        print(f"[DIGIKEY] URL: {url}")
        response = Wrappers.get_request(self, url, headers=header)

        print(f"[DIGIKEY] Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"[DIGIKEY] ✗ Order history request failed: {response.status_code}")
            print(f"[DIGIKEY] Response body: {response.text[:500]}")
            return {'error_status': f'API error: {response.status_code} - {response.text[:200]}', 'orders': []}

        try:
            response_data = response.json()
            print(f"[DIGIKEY] Response data type: {type(response_data)}")
            print(f"[DIGIKEY] Response data: {str(response_data)[:500]}")
        except Exception as e:
            print(f"[DIGIKEY] ✗ Failed to parse response: {e}")
            print(f"[DIGIKEY] Raw response: {response.text[:500]}")
            return {'error_status': str(e), 'orders': []}

        # Parse the order list
        orders = []
        for order in response_data:
            orders.append({
                'salesorder_id': order.get('SalesorderId') or order.get('salesorder_id'),
                'date_entered': order.get('DateEntered') or order.get('date_entered'),
                'purchase_order': order.get('PurchaseOrder') or order.get('purchase_order', ''),
                'customer_id': order.get('CustomerId') or order.get('customer_id')
            })

        print(f"[DIGIKEY] ✓ Found {len(orders)} orders")
        return {'error_status': 'OK', 'orders': orders}

    def get_digikey_order_details(self, salesorder_id):
        """
        Get detailed order information including line items with actual prices.
        """
        print(f"\n[DIGIKEY] Getting order details for order {salesorder_id}...")

        # Refresh token first
        token = Digikey.refresh_digikey_access_token(self)
        if token['status_code'] != 200:
            print(f"[DIGIKEY] ✗ Token refresh failed: {token['message']}")
            return {'error_status': token['message']}

        # Use /Status endpoint (per Digikey API spec)
        url = f'https://api.digikey.com/OrderDetails/v3/Status/{salesorder_id}'
        header = {
            'Authorization': f"Bearer {self.get_setting('DIGIKEY_TOKEN')}",
            'X-DIGIKEY-Client-Id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'accept': 'application/json'
        }

        print(f"[DIGIKEY] Fetching order {salesorder_id}")
        response = Wrappers.get_request(self, url, headers=header)

        if response.status_code != 200:
            print(f"[DIGIKEY] ✗ Order details request failed: {response.status_code}")
            return {'error_status': f'API error: {response.status_code}'}

        try:
            order_data = response.json()
        except Exception as e:
            print(f"[DIGIKEY] ✗ Failed to parse response: {e}")
            return {'error_status': str(e)}

        # Log full response for debugging extra fields
        print(f"[DIGIKEY] Order response keys: {order_data.keys()}")

        # Extract shipping details - costs are often nested here
        shipping_details = order_data.get('ShippingDetails') or order_data.get('shipping_details') or []
        print(f"[DIGIKEY] ShippingDetails: {shipping_details}")

        # Sum up shipping costs from all shipments
        shipping_cost = 0.0
        tax = 0.0
        tariff = 0.0

        if isinstance(shipping_details, list):
            for shipment in shipping_details:
                shipping_cost += float(shipment.get('ShippingCost') or shipment.get('shipping_cost') or 0)
                tax += float(shipment.get('Tax') or shipment.get('tax') or 0)
                tariff += float(shipment.get('Tariff') or shipment.get('tariff') or shipment.get('Duty') or shipment.get('duty') or 0)
        elif isinstance(shipping_details, dict):
            shipping_cost = float(shipping_details.get('ShippingCost') or shipping_details.get('shipping_cost') or 0)
            tax = float(shipping_details.get('Tax') or shipping_details.get('tax') or 0)
            tariff = float(shipping_details.get('Tariff') or shipping_details.get('tariff') or shipping_details.get('Duty') or shipping_details.get('duty') or 0)

        # Also check top-level fields
        if shipping_cost == 0:
            shipping_cost = float(order_data.get('ShippingCost') or order_data.get('shipping_cost') or 0)
        if tax == 0:
            tax = float(order_data.get('Tax') or order_data.get('tax') or 0)
        if tariff == 0:
            tariff = float(order_data.get('Tariff') or order_data.get('tariff') or order_data.get('Duty') or order_data.get('duty') or 0)

        # Parse the order details
        result = {
            'error_status': 'OK',
            'salesorder_id': order_data.get('SalesorderId') or order_data.get('salesorder_id'),
            'purchase_order': order_data.get('PurchaseOrder') or order_data.get('purchase_order', ''),
            'customer_id': order_data.get('CustomerId') or order_data.get('customer_id'),
            'currency': order_data.get('Currency') or order_data.get('currency', 'USD'),
            'line_items': [],
            # Extra costs
            'shipping_cost': shipping_cost,
            'tax': tax,
            'tariff': tariff,
            'merchandise_total': float(order_data.get('MerchandiseTotal') or order_data.get('merchandise_total') or 0),
            'order_total': float(order_data.get('OrderTotal') or order_data.get('order_total') or 0),
        }

        # Log extra costs found
        print(f"[DIGIKEY] Extra costs - Shipping: ${result['shipping_cost']}, Tax: ${result['tax']}, Tariff: ${result['tariff']}")

        # Parse line items
        raw_items = order_data.get('LineItems') or order_data.get('line_items', [])
        for item in raw_items:
            result['line_items'].append({
                'digi_key_part_number': item.get('DigiKeyPartNumber') or item.get('digi_key_part_number', ''),
                'manufacturer_part_number': item.get('ManufacturerPartNumber') or item.get('manufacturer_part_number', ''),
                'product_description': item.get('ProductDescription') or item.get('product_description', ''),
                'quantity': item.get('Quantity') or item.get('quantity', 0),
                'unit_price': float(item.get('UnitPrice') or item.get('unit_price', 0)),
                'total_price': float(item.get('TotalPrice') or item.get('total_price', 0)),
                'invoice_id': item.get('InvoiceId') or item.get('invoice_id'),
                'customer_reference': item.get('CustomerReference') or item.get('customer_reference', '')
            })

        print(f"[DIGIKEY] ✓ Order {salesorder_id} has {len(result['line_items'])} line items")
        return result
