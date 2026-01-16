from django.http import HttpResponse
from django.http import JsonResponse
from django.urls import re_path

from order.api import PurchaseOrderDetail
from order.models import PurchaseOrder, PurchaseOrderExtraLine
from part.api import PartDetail
from part.models import Part, PartParameter, PartParameterTemplate, PartCategory
from plugin import InvenTreePlugin
from plugin.mixins import UserInterfaceMixin, SettingsMixin, UrlsMixin
from company.models import Company, ManufacturerPart, SupplierPart
from company.models import SupplierPriceBreak
from users.permissions import check_user_role
from common.models import InvenTreeSetting
from .version import PLUGIN_VERSION
from .mouser import Mouser
from .digikey import Digikey
from .farnell import Farnell
from .meta_access import MetaAccess
from .request_wrappers import Wrappers

import json
from datetime import datetime


class SupplierCartPanel(UserInterfaceMixin, SettingsMixin, InvenTreePlugin, UrlsMixin):

    PurchaseOrderPK = 0

    NAME = "SupplierCart"
    SLUG = "suppliercart"
    TITLE = "Create Shopping Cart"
    AUTHOR = "Michael"
    PUBLISH_DATE = "2025-08-21:00:00"
    DESCRIPTION = "This plugin allows to transfer a PO into a supplier shopping cart."
    VERSION = PLUGIN_VERSION
    COUNTRY_CODES = {'AUD': 'AU',
                     'CAD': 'CA',
                     'CNY': 'CN',
                     'GBP': 'GB',
                     'JPY': 'JP',
                     'NZD': 'NZ',
                     'USD': 'US',
                     'EUR': 'DE'
                     }

    SETTINGS = {
        'MOUSER_PK': {
            'name': 'Mouser Supplier ID',
            'description': 'Primary key of the Mouser supplier',
            'model': 'company.company',
        },
        'DIGIKEY_PK': {
            'name': 'Digikey Supplier ID',
            'description': 'Primary key of the Digikey supplier',
            'model': 'company.company',
        },
        'FARNELL_PK': {
            'name': 'Farnell Supplier ID',
            'description': 'Primary key of the Farnell supplier',
            'model': 'company.company',
        },
        'MOUSERCARTKEY': {
            'name': 'Mouser cart API key',
            'description': 'Place here your key for the Mouser shopping cart API',
        },
        'MOUSERSEARCHKEY': {
            'name': 'Mouser search API key',
            'description': 'Place here your key for the Mouser search API',
        },
        'MOUSERLANGUAGE': {
            'name': 'Mouser language',
            'description': 'The language that Mouser uses to answer your requests',
            'choices': [('English', 'Mouser answers in English'),
                        ('German', 'Mouser answers in German')],
            'default': 'German',
        },
        'FARNELLSEARCHKEY': {
            'name': 'Farnell search API key',
            'description': 'Place here your key for the Farnell search API',
        },
        'DIGIKEY_CLIENT_ID': {
            'name': 'Digikey ID',
            'description': 'Client ID for Digikey',
        },
        'DIGIKEY_CLIENT_SECRET': {
            'name': 'Digikey Secret',
            'description': 'Client secret for Digikey',
        },
        'DIGIKEY_TOKEN': {
            'name': 'Digikey token',
            'description': 'Token for Digikey',
        },
        'DIGIKEY_REFRESH_TOKEN': {
            'name': 'Digikey refresh token',
            'description': 'Digikey Refresh token',
        },
        'PROXY_CON': {
            'name': 'Proxy CON',
            'description': 'Connection protocol to proxy server if needed e.g. https',
        },
        'PROXY_URL': {
            'name': 'Proxy URL',
            'description': 'URL to proxy server if needed e.g. http://user:password@ipaddress:port',
        },
        'DIGIKEY_CATEGORY_MAP': {
            'name': 'Digikey Category Mapping',
            'description': 'JSON mapping of Digikey categories to InvenTree categories. Format: {"Digikey Category": "InvenTree Category"}',
            'default': '{"Resistors": "Resistors", "Capacitors": "Capacitors", "Transistors": "Transistors", "Connectors": "Connectors", "Integrated Circuits (ICs)": "Integrated Circuits", "Discrete Semiconductor Products": "Diodes", "Crystals, Oscillators, Resonators": "Oscillators", "Connectors, Interconnects": "Connectors", "Inductors, Coils, Chokes": "Inductors", "Circuit Protection": "Other", "Embedded Computers": "Boards", "Development Boards, Kits, Programmers": "Boards", "Potentiometers, Variable Resistors": "Resistors", "Optoelectronics": "Integrated Circuits", "Filters": "Other"}',
        },
        'DIGIKEY_PARAMETER_MAP': {
            'name': 'Digikey Parameter Mapping',
            'description': 'JSON mapping of Digikey parameter names to InvenTree parameter names. Format: {"Digikey Param": "InvenTree Param"}',
            'default': '{"Resistance": "Resistance", "Tolerance": "Tolerance", "Power (Watts)": "Power", "Package / Case": "Package", "Voltage - Rated": "Voltage", "Capacitance": "Capacitance", "Inductance": "Inductance"}',
        },
        'IMPORT_HTSUS': {
            'name': 'Import HTSUS Codes',
            'description': 'Enable importing HTSUS (Harmonized Tariff Schedule) codes from Digikey',
            'default': True,
            'validator': bool,
        },
    }

# ----------------------------------------------------------------------------
# Here we check the settings and show som status messages. We also construct
# the Digikey redirect_uri that needs to put into the Digikey web page.
# If the pk of the supplier is not set ein tne settings, the supplier is
# disabled. The button for Digikey token creation is also here.

    def get_settings_content(self, request):
        client_id = self.get_setting('DIGIKEY_CLIENT_ID')
        base_url = InvenTreeSetting.get_setting('INVENTREE_BASE_URL')
        if base_url == '':
            base_url_state = '<span class="badge badge-left rounded-pill bg-danger">Missing</span>'
        elif base_url[0:5] != 'https':
            base_url_state = '<span class="badge badge-left rounded-pill bg-danger">Server does not run https</span>'
        else:
            base_url_state = '<span class="badge badge-left rounded-pill bg-success">OK</span>'
        redirect_uri = f'{base_url}/{self.base_url}digikeytoken/'
        url = f'https://api.digikey.com/v1/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}'
        return f"""
        <p>Setup:</p>
        <ol>
        <li>Read the <a href="https://github.com/SergeoLacruz/inventree-supplier-panel"> docu </a> on github</li>
        <li>Enable the plugin</li>
        <li>Put all required keys into settings</li>
        <li>Enjoy</li>
        <li>Remove the shopping carts and lists regularly from your accounts</li>
        </ol>
        <p>Status:</p>
        <table class='table table-condensed'>
           <tr>
           <td>Server Base URL</td><td>{base_url_state}</td>
           </tr>
           <tr>
           <td>Callback URL (Add this to your Digikey account)</td><td>{redirect_uri}</td>
           </tr>
        </table>
        <a class="btn btn-dark" onclick="window.open('{url}','name','width=1000px,height=800px')"">
         Create Digikey Token
        </a>
        """

# ----------------------------------------------------------------------------
# Create the panels using the new UserInterfaceMixin API

    def get_ui_panels(self, request, context, **kwargs):
        """Return custom panels for Purchase Orders and Parts."""
        panels = []
        target_model = context.get('target_model')
        target_id = context.get('target_id')
        
        print(f"\n[GET_UI_PANELS] Called with target_model={target_model}, target_id={target_id}")

        # Load registered suppliers from settings
        self._load_registered_suppliers()
        
        print(f"[GET_UI_PANELS] Registered suppliers:")
        for name, info in self.registered_suppliers.items():
            print(f"  {name}: is_registered={info.get('is_registered')}, pk={info.get('pk')}")

        # For Purchase Orders: PO transfer panels
        if target_model == 'purchaseorder' and target_id:
            print(f"[GET_UI_PANELS] Processing purchase order {target_id}")
            # Check permissions
            has_permission = (
                check_user_role(request.user, 'purchase_order', 'change') or
                check_user_role(request.user, 'purchase_order', 'delete') or
                check_user_role(request.user, 'purchase_order', 'add')
            )
            
            print(f"[GET_UI_PANELS] User has permission: {has_permission}")

            if not has_permission:
                return panels

            # Get the PO and check supplier
            try:
                po = PurchaseOrder.objects.get(pk=target_id)
                print(f"[GET_UI_PANELS] PO supplier: {po.supplier.name} (PK: {po.supplier.pk})")
            except PurchaseOrder.DoesNotExist:
                print(f"[GET_UI_PANELS] PO not found")
                return panels

            # Add panel for Digikey supplier
            if (self.registered_suppliers.get('Digikey', {}).get('is_registered') and
                po.supplier.pk == self.registered_suppliers['Digikey']['pk']):
                print(f"[GET_UI_PANELS] Adding Digikey panel")
                # Build OAuth URL for token regeneration
                client_id = self.get_setting('DIGIKEY_CLIENT_ID')
                base_url = InvenTreeSetting.get_setting('INVENTREE_BASE_URL')
                redirect_uri = f'{base_url}/{self.base_url}digikeytoken/'
                oauth_url = f'https://api.digikey.com/v1/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}'
                panels.append({
                    'key': 'digikey-po-transfer',
                    'title': 'Digikey Actions',
                    'icon': 'tabler:shopping-cart',
                    'source': self.plugin_static_file('po_transfer_panel.js:renderDigikeyPanel'),
                    'context': {
                        'po_pk': target_id,
                        'supplier': 'Digikey',
                        'oauth_url': oauth_url
                    }
                })

            # Add panel for Mouser supplier
            if (self.registered_suppliers.get('Mouser', {}).get('is_registered') and
                po.supplier.pk == self.registered_suppliers['Mouser']['pk']):
                print(f"[GET_UI_PANELS] Adding Mouser panel")
                panels.append({
                    'key': 'mouser-po-transfer',
                    'title': 'Mouser Actions',
                    'icon': 'tabler:shopping-cart',
                    'source': self.plugin_static_file('po_transfer_panel.js:renderMouserPanel'),
                    'context': {
                        'po_pk': target_id,
                        'supplier': 'Mouser'
                    }
                })

            # Add panel for Farnell supplier (if implemented in the future)
            if (self.registered_suppliers.get('Farnell', {}).get('is_registered') and
                po.supplier.pk == self.registered_suppliers['Farnell']['pk']):
                # Farnell panel would go here
                pass

        # For Parts Category: Import Parts panel (shown on main parts page)
        if target_model == 'partcategory':
            print(f"[GET_UI_PANELS] Adding Import Parts panel for parts category")
            panels.append({
                'key': 'import-parts',
                'title': 'Import Parts from Supplier',
                'icon': 'tabler:package-import',
                'source': self.plugin_static_file('import_parts_ui.js:renderImportPartsPage'),
                'context': {}
            })

        # For Parts: Supplier part creation panel
        if target_model == 'part' and target_id:
            # Check permissions
            has_permission = (
                check_user_role(request.user, 'part', 'change') or
                check_user_role(request.user, 'part', 'delete') or
                check_user_role(request.user, 'part', 'add')
            )

            if not has_permission:
                return panels

            # Check if any supplier is registered
            show_panel = any(
                self.registered_suppliers.get(s, {}).get('is_registered', False)
                for s in ['Digikey', 'Mouser', 'Farnell']
            )

            if show_panel:
                try:
                    part = Part.objects.get(pk=target_id)
                    if part.purchaseable:
                        panels.append({
                            'key': 'supplier-lookup',
                            'title': 'Automatic Supplier Parts',
                            'icon': 'ti:search:outline',
                            'source': self.plugin_static_file('supplier_lookup_panel.js'),
                            'context': {'part_pk': target_id}
                        })
                except Part.DoesNotExist:
                    pass

        return panels

    def _load_registered_suppliers(self):
        """Helper to load supplier PKs from settings."""
        try:
            self.registered_suppliers['Digikey']['pk'] = int(self.get_setting('DIGIKEY_PK'))
            self.registered_suppliers['Digikey']['is_registered'] = True
        except Exception:
            self.registered_suppliers['Digikey']['is_registered'] = False

        try:
            self.registered_suppliers['Mouser']['pk'] = int(self.get_setting('MOUSER_PK'))
            self.registered_suppliers['Mouser']['is_registered'] = True
        except Exception:
            self.registered_suppliers['Mouser']['is_registered'] = False

        try:
            self.registered_suppliers['Farnell']['pk'] = int(self.get_setting('FARNELL_PK'))
            self.registered_suppliers['Farnell']['is_registered'] = True
        except Exception:
            self.registered_suppliers['Farnell']['is_registered'] = False

    def setup_urls(self):
        return [
            # This one is for the Digikey OAuth callback
            re_path(r'^digikeytoken/', self.receive_authcode, name='digikeytoken'),

            # Now for the plugin
            re_path(r'transfercart/(?P<pk>\d+)/', self.transfer_cart, name='transfer-cart'),
            re_path(r'addsupplierpart(?:\.(?P<format>json))?$', self.add_supplierpart, name='add-supplierpart'),
            re_path(r'importfullpart(?:\.(?P<format>json))?$', self.import_full_part, name='import-full-part'),

            # Digikey order import endpoints
            re_path(r'digikeyorders/', self.get_digikey_orders, name='digikey-orders'),
            re_path(r'importorder/(?P<pk>\d+)/', self.import_digikey_order, name='import-order'),
            re_path(r'addextracosts/(?P<pk>\d+)/', self.add_extra_costs, name='add-extra-costs'),
        ]

# --------------------------- get_partdata ------------------------------------
# This is just the wrapper that selects the proper supplier dependant function
    def get_partdata(self, supplier, sku, options):
        print(f"\n[GET_PARTDATA] Called with:")
        print(f"  Supplier: {supplier}")
        print(f"  SKU: {sku}")
        print(f"  Options: {options}")

        try:
            self.registered_suppliers['Mouser']['pk'] = int(self.get_setting('MOUSER_PK'))
            print(f"  Mouser PK: {self.registered_suppliers['Mouser']['pk']}")
        except Exception as e:
            print(f"  Mouser PK not configured: {e}")
            pass
        try:
            self.registered_suppliers['Digikey']['pk'] = int(self.get_setting('DIGIKEY_PK'))
            print(f"  Digikey PK: {self.registered_suppliers['Digikey']['pk']}")
        except Exception as e:
            print(f"  Digikey PK not configured: {e}")
            pass
        try:
            self.registered_suppliers['Farnell']['pk'] = int(self.get_setting('FARNELL_PK'))
            print(f"  Farnell PK: {self.registered_suppliers['Farnell']['pk']}")
        except Exception as e:
            print(f"  Farnell PK not configured: {e}")
            pass

        part_data = {}
        print(f"  Searching for supplier match in registered_suppliers...")
        print(f"  Requested supplier type: {type(supplier)}, value: {supplier}")
        
        # Convert supplier to int if it's not already
        try:
            supplier_int = int(supplier)
        except (ValueError, TypeError):
            supplier_int = supplier
            
        for s in self.registered_suppliers:
            registered_pk = self.registered_suppliers[s].get('pk')
            print(f"    Checking: {s} (pk={registered_pk}, type={type(registered_pk)}) vs requested supplier: {supplier_int} (type={type(supplier_int)})")
            if supplier_int == registered_pk:
                print(f"    ✓ Match found! Calling {s} get_partdata function...")
                part_data = self.registered_suppliers[s]['get_partdata'](self, sku, options)
                break
        else:
            print(f"  ✗ No matching supplier found for: {supplier}")
            part_data['error_status'] = f'Supplier not found or not configured: {supplier}'
            part_data['number_of_results'] = 0
        
        print(f"  Returning part_data with error_status: {part_data.get('error_status')}, results: {part_data.get('number_of_results')}")
        return part_data

# --------------------------- receive_authcode --------------------------------
# This creates the Digikey token from the authcode

    def receive_authcode(self, request):
        auth_code = request.GET.get('code')
        url = 'https://api.digikey.com/v1/oauth2/token'
        redirect_uri = InvenTreeSetting.get_setting('INVENTREE_BASE_URL') + '/' + self.base_url + 'digikeytoken/'
        url_data = {
            'code': auth_code,
            'client_id': self.get_setting('DIGIKEY_CLIENT_ID'),
            'client_secret': self.get_setting('DIGIKEY_CLIENT_SECRET'),
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        header = {}
        response = Wrappers.post_request(self, url_data, url, headers=header)
        if response.status_code == 200:
            print('\033[32mAccess Token get SUCCESS\033[0m')
            response_data = response.json()
            self.set_setting('DIGIKEY_TOKEN', response_data['access_token'])
            self.set_setting('DIGIKEY_REFRESH_TOKEN', response_data['refresh_token'])
            return HttpResponse('New Digikey token successfully received')
        else:
            print('\033[31m\033[1mReceive access token FAILED\033[0m')
            return HttpResponse(response.content)

# --------------------------- transfer_cart ------------------------------------
# This is called when the button is pressed and does most of the work.

    def transfer_cart(self, request, pk):

        self.PurchaseOrderPK = int(pk)
        order = PurchaseOrder.objects.filter(id=pk).all()[0]
        try:
            self.registered_suppliers['Mouser']['pk'] = int(self.get_setting('MOUSER_PK'))
        except Exception:
            pass
        try:
            self.registered_suppliers['Digikey']['pk'] = int(self.get_setting('DIGIKEY_PK'))
        except Exception:
            pass
        for s in self.registered_suppliers:
            if order.supplier.pk == self.registered_suppliers[s]['pk']:
                supplier = s

        # First create the shopping cart
        cart_data = self.registered_suppliers[supplier]['create_cart'](self, order)
        if cart_data['error_status'] != 'OK':
            cart_data['message'] = cart_data['error_status']
            return JsonResponse(cart_data)

        # Then fill it
        cart_data = self.registered_suppliers[supplier]['update_cart'](self, order, cart_data['ID'])
        if cart_data['error_status'] != 'OK':
            cart_data['message'] = cart_data['error_status']
            return JsonResponse(cart_data)

        # Now we transfer the actual prices back into the PO
        for po_item in order.lines.all():
            for item in cart_data['CartItems']:
                if po_item.part.SKU == item['SKU']:
                    po_item.purchase_price = item['UnitPrice']
                    po_item.save()
        cart_data['message'] = 'OK'
        cart_data['pk'] = pk
        cart_data['cart_date'] = datetime.today().strftime('%Y-%m-%d')
        MetaAccess.set_value(self, order, 'cart', cart_data)
        return JsonResponse(cart_data)

# ---------------------------- get_digikey_orders ------------------------------
# Returns list of recent Digikey orders for dropdown selection

    def get_digikey_orders(self, request):
        """Get list of recent Digikey orders for import selection."""
        print(f"\n[GET_DIGIKEY_ORDERS] Fetching recent Digikey orders...")

        # Get order history from Digikey
        result = Digikey.get_digikey_order_history(self, days_back=90)

        if result['error_status'] != 'OK':
            return JsonResponse({
                'message': result['error_status'],
                'orders': []
            })

        return JsonResponse({
            'message': 'OK',
            'orders': result['orders']
        })

# ---------------------------- import_digikey_order ----------------------------
# Imports actual prices and order number from a placed Digikey order

    def import_digikey_order(self, request, pk):
        """
        Import order data from Digikey into InvenTree PO.
        Updates line item prices, stores order number, and marks PO as placed.
        """
        print(f"\n[IMPORT_DIGIKEY_ORDER] ========================================")
        print(f"[IMPORT_DIGIKEY_ORDER] PO PK: {pk}")

        # Get the PO
        try:
            order = PurchaseOrder.objects.get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return JsonResponse({'message': 'Purchase order not found'}, status=404)

        # Parse request body
        try:
            data = json.loads(request.body)
            salesorder_id = data.get('salesorder_id')
            use_recent = data.get('use_recent', False)
        except json.JSONDecodeError:
            salesorder_id = None
            use_recent = True

        print(f"[IMPORT_DIGIKEY_ORDER] salesorder_id: {salesorder_id}, use_recent: {use_recent}")

        # If use_recent, get the most recent order
        if use_recent or not salesorder_id:
            print("[IMPORT_DIGIKEY_ORDER] Fetching most recent order...")
            history = Digikey.get_digikey_order_history(self, days_back=30)
            if history['error_status'] != 'OK':
                return JsonResponse({'message': history['error_status']})
            if not history['orders']:
                return JsonResponse({'message': 'No recent Digikey orders found'})
            salesorder_id = history['orders'][0]['salesorder_id']
            print(f"[IMPORT_DIGIKEY_ORDER] Using most recent order: {salesorder_id}")

        # Get order details from Digikey
        order_data = Digikey.get_digikey_order_details(self, salesorder_id)
        if order_data['error_status'] != 'OK':
            return JsonResponse({'message': order_data['error_status']})

        # Match and update line items
        matched_items = []
        unmatched_items = []

        # Log all Digikey SKUs for debugging
        dk_skus = [item['digi_key_part_number'] for item in order_data['line_items']]
        print(f"[IMPORT_DIGIKEY_ORDER] Digikey order SKUs: {dk_skus}")

        def normalize_digikey_sku(sku):
            """Normalize Digikey SKU by removing packaging suffixes for comparison.

            Digikey uses suffixes like:
            - -1-ND, -2-ND, -6-ND (numeric packaging codes)
            - CT-ND (Cut Tape), TR-ND (Tape & Reel), DKR-ND (Digi-Reel)
            """
            import re
            if not sku:
                return ''
            # Remove -ND suffix first
            s = sku.rstrip('-ND').rstrip('-nd')
            if s.endswith('-ND') or s.endswith('-nd'):
                s = s[:-3]
            # Remove packaging suffixes: -1, -2, -6, CT, TR, DKR
            s = re.sub(r'(-[126]|CT|TR|DKR)$', '', s, flags=re.IGNORECASE)
            return s.upper()

        for po_item in order.lines.all():
            sku = po_item.part.SKU
            sku_normalized = normalize_digikey_sku(sku)
            print(f"[IMPORT_DIGIKEY_ORDER] Looking for PO SKU: '{sku}' (normalized: '{sku_normalized}')")
            matched = False

            for dk_item in order_data['line_items']:
                dk_sku = dk_item['digi_key_part_number']
                dk_sku_normalized = normalize_digikey_sku(dk_sku)
                # Match on normalized SKUs (ignoring packaging differences)
                if dk_sku_normalized == sku_normalized:
                    # Update price
                    old_price = po_item.purchase_price
                    po_item.purchase_price = dk_item['unit_price']
                    po_item.save()

                    # Handle Money objects - get the amount as float
                    if old_price:
                        old_price_float = float(old_price.amount) if hasattr(old_price, 'amount') else float(old_price)
                    else:
                        old_price_float = 0.0

                    matched_items.append({
                        'SKU': sku,
                        'old_price': old_price_float,
                        'new_price': dk_item['unit_price'],
                        'quantity': dk_item['quantity']
                    })
                    matched = True
                    print(f"[IMPORT_DIGIKEY_ORDER] ✓ Matched {sku} -> {dk_sku}: ${old_price_float} -> ${dk_item['unit_price']}")
                    break

            if not matched:
                unmatched_items.append({'SKU': sku})
                print(f"[IMPORT_DIGIKEY_ORDER] ✗ No match for {sku}")

        # Store Digikey order info in PO metadata
        MetaAccess.set_value(self, order, 'DigiKeyOrderId', str(salesorder_id))
        MetaAccess.set_value(self, order, 'DigiKeyOrderDate', datetime.today().strftime('%Y-%m-%d'))
        if order_data.get('line_items') and order_data['line_items'][0].get('invoice_id'):
            MetaAccess.set_value(self, order, 'DigiKeyInvoiceId', str(order_data['line_items'][0]['invoice_id']))

        # Update PO fields with Digikey order info
        # Set supplier_reference to the Digikey order number
        order.supplier_reference = str(salesorder_id)
        # Set link to the Digikey order page
        order.link = f'https://www.digikey.com/en/mylists/order/{salesorder_id}'
        order.save()
        print(f"[IMPORT_DIGIKEY_ORDER] ✓ Updated PO supplier_reference={salesorder_id}, link={order.link}")

        # Store tracking info
        if order_data.get('tracking'):
            tracking_info = order_data['tracking'][0] if order_data['tracking'] else {}
            if tracking_info:
                MetaAccess.set_value(self, order, 'DigiKeyCarrier', tracking_info.get('carrier', ''))
                MetaAccess.set_value(self, order, 'DigiKeyTrackingNumber', tracking_info.get('tracking_number', ''))
                MetaAccess.set_value(self, order, 'DigiKeyTrackingUrl', tracking_info.get('tracking_url', ''))
                MetaAccess.set_value(self, order, 'DigiKeyShippingMethod', tracking_info.get('shipping_method', ''))
                MetaAccess.set_value(self, order, 'DigiKeyDeliveryDate', tracking_info.get('delivery_date', ''))
                print(f"[IMPORT_DIGIKEY_ORDER] ✓ Saved tracking: {tracking_info.get('carrier')} - {tracking_info.get('tracking_number')}")

        # Add extra line items for shipping, tax, and tariffs
        extra_lines_added = []
        currency = order_data.get('currency', 'USD')

        # Helper to add or update extra line
        def add_extra_line(description, price, reference=''):
            if price and price > 0:
                # Check if line already exists
                existing = PurchaseOrderExtraLine.objects.filter(
                    order=order,
                    description=description
                ).first()
                if existing:
                    existing.price = price
                    existing.save()
                    print(f"[IMPORT_DIGIKEY_ORDER] ✓ Updated extra line: {description} = ${price}")
                else:
                    PurchaseOrderExtraLine.objects.create(
                        order=order,
                        description=description,
                        quantity=1,
                        price=price,
                        price_currency=currency,
                        reference=reference
                    )
                    print(f"[IMPORT_DIGIKEY_ORDER] ✓ Added extra line: {description} = ${price}")
                extra_lines_added.append({'description': description, 'price': price})

        # Add shipping cost
        if order_data.get('shipping_cost'):
            add_extra_line('Shipping', order_data['shipping_cost'], f'DK Order {salesorder_id}')

        # Add tax
        if order_data.get('tax'):
            add_extra_line('Tax', order_data['tax'], f'DK Order {salesorder_id}')

        # Add tariff/duty
        if order_data.get('tariff'):
            add_extra_line('Tariff/Duty', order_data['tariff'], f'DK Order {salesorder_id}')

        # Note: Not automatically marking PO as "Placed" - user should review and approve

        # Prepare tracking info for response
        tracking_response = None
        if order_data.get('tracking') and len(order_data['tracking']) > 0:
            t = order_data['tracking'][0]
            tracking_response = {
                'carrier': t.get('carrier', ''),
                'tracking_number': t.get('tracking_number', ''),
                'tracking_url': t.get('tracking_url', ''),
                'shipping_method': t.get('shipping_method', ''),
                'delivery_date': t.get('delivery_date', '')
            }

        result = {
            'message': 'OK',
            'salesorder_id': salesorder_id,
            'matched_count': len(matched_items),
            'unmatched_count': len(unmatched_items),
            'matched_items': matched_items,
            'unmatched_items': unmatched_items,
            'extra_lines': extra_lines_added,
            'currency': order_data.get('currency', 'USD'),
            'tracking': tracking_response
        }

        print(f"[IMPORT_DIGIKEY_ORDER] ========================================")
        print(f"[IMPORT_DIGIKEY_ORDER] ✓ Import complete: {len(matched_items)} matched, {len(unmatched_items)} unmatched")

        return JsonResponse(result)

# ---------------------------- add_extra_costs -------------------------------
    def add_extra_costs(self, request, pk):
        """Add extra cost line items (shipping, tax, tariff) to a PO."""
        print(f"\n[ADD_EXTRA_COSTS] ========================================")
        print(f"[ADD_EXTRA_COSTS] PO PK: {pk}")

        try:
            order = PurchaseOrder.objects.get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return JsonResponse({'message': f'PO with pk={pk} not found'}, status=404)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON'}, status=400)

        shipping = float(data.get('shipping', 0) or 0)
        tax = float(data.get('tax', 0) or 0)
        tariff = float(data.get('tariff', 0) or 0)

        print(f"[ADD_EXTRA_COSTS] Shipping: ${shipping}, Tax: ${tax}, Tariff: ${tariff}")

        # Get currency from settings
        currency = InvenTreeSetting.get_setting('INVENTREE_DEFAULT_CURRENCY') or 'USD'
        added_lines = []

        # Helper to add or update extra line
        def add_or_update_line(description, price):
            if price and price > 0:
                # Check if line already exists
                existing = PurchaseOrderExtraLine.objects.filter(
                    order=order,
                    description=description
                ).first()
                if existing:
                    existing.price = price
                    existing.save()
                    print(f"[ADD_EXTRA_COSTS] ✓ Updated: {description} = ${price}")
                else:
                    PurchaseOrderExtraLine.objects.create(
                        order=order,
                        description=description,
                        quantity=1,
                        price=price,
                        price_currency=currency
                    )
                    print(f"[ADD_EXTRA_COSTS] ✓ Added: {description} = ${price}")
                added_lines.append(f"{description}: ${price:.2f}")

        if shipping > 0:
            add_or_update_line('Shipping', shipping)
        if tax > 0:
            add_or_update_line('Tax', tax)
        if tariff > 0:
            add_or_update_line('Tariff/Duty', tariff)

        if not added_lines:
            return JsonResponse({'message': 'No costs provided'})

        print(f"[ADD_EXTRA_COSTS] ✓ Complete: {added_lines}")
        return JsonResponse({
            'message': 'OK',
            'added_lines': added_lines
        })

# ---------------------------- add_supplierpart -------------------------------
    def add_supplierpart(self, request):
        data = json.loads(request.body)
        part = Part.objects.filter(id=data['pk'])[0]
        
        print(f"\n[ADD_SUPPLIER_PART] ================================================")
        print(f"[ADD_SUPPLIER_PART] Request data: {data}")
        print(f"[ADD_SUPPLIER_PART] InvenTree Part ID: {part.pk}")
        print(f"[ADD_SUPPLIER_PART] InvenTree Part Name: {part.name}")
        print(f"[ADD_SUPPLIER_PART] InvenTree Part IPN: {part.IPN}")
        
        # Map supplier name to PK (data['supplier'] is the name like 'digikey' or 'mouser')
        supplier_name = data['supplier'].lower()
        supplier_map = {
            'digikey': self.get_setting('DIGIKEY_PK'),
            'mouser': self.get_setting('MOUSER_PK'),
            'farnell': self.get_setting('FARNELL_PK')
        }
        
        supplier_pk = supplier_map.get(supplier_name)
        print(f"[ADD_SUPPLIER_PART] Supplier: {supplier_name}, PK: {supplier_pk}")
        
        if not supplier_pk:
            return JsonResponse({"message": f"Supplier '{data['supplier']}' not configured"})
        
        supplier = Company.objects.filter(id=supplier_pk)[0]
        
        data['sku'] = data['sku'].strip()
        print(f"[ADD_SUPPLIER_PART] SKU after strip: '{data['sku']}'")
        
        if (data['sku'] == ''):
            print(f"[ADD_SUPPLIER_PART] ✗ Empty SKU")
            return JsonResponse({"message": "Please provide part number"})
        
        manufacturer_part = ManufacturerPart.objects.filter(part=data['pk'])
        print(f"[ADD_SUPPLIER_PART] Manufacturer parts query returned {len(manufacturer_part)} results")
        
        if len(manufacturer_part) == 0:
            print(f"[ADD_SUPPLIER_PART] ✗ Part has no manufacturer part - this is required!")
            return JsonResponse({"message": "Part has no manufacturer part"})
        
        # Show details of manufacturer parts
        for idx, mp in enumerate(manufacturer_part):
            print(f"[ADD_SUPPLIER_PART] Manufacturer Part {idx+1}:")
            print(f"  - PK: {mp.pk}")
            print(f"  - MPN: {mp.MPN}")
            print(f"  - Manufacturer: {mp.manufacturer.name if mp.manufacturer else 'None'}")
        
        # Check existing supplier parts
        supplier_parts = SupplierPart.objects.filter(part=data['pk'])
        print(f"[ADD_SUPPLIER_PART] Found {len(supplier_parts)} existing supplier parts for this InvenTree part")
        
        for idx, sp in enumerate(supplier_parts):
            print(f"[ADD_SUPPLIER_PART] Existing Supplier Part {idx+1}:")
            print(f"  - Supplier: {sp.supplier.name}")
            print(f"  - SKU: '{sp.SKU}'")
            print(f"  - MPN: {sp.manufacturer_part.MPN if sp.manufacturer_part else 'None'}")
        
        for sp in supplier_parts:
            if sp.SKU.strip() == data['sku']:
                print(f"[ADD_SUPPLIER_PART] ✗ Supplier part with SKU '{data['sku']}' already exists!")
                return JsonResponse({"message": "Supplierpart with this SKU already exists"})

        # Call get_partdata with the supplier PK (integer), not the name
        print(f"[ADD_SUPPLIER_PART] Calling get_partdata(supplier_pk={supplier_pk}, sku='{data['sku']}', options='exact')")
        
        # Here start the new interface
        data_result = self.get_partdata(supplier_pk, data['sku'], 'exact')
        
        print(f"[ADD_SUPPLIER_PART] Result: error_status={data_result.get('error_status')}, num_results={data_result.get('number_of_results')}")
        
        if data_result['error_status'] != 'OK':
            return JsonResponse({"message": data_result['error_status']})
        if data_result['number_of_results'] == 0:
            return JsonResponse({"message": "Part not found"})
        sp = SupplierPart.objects.create(part=part,
                                         supplier=supplier,
                                         manufacturer_part=manufacturer_part[0],
                                         SKU=data_result['SKU'],
                                         link=data_result['URL'],
                                         note=data_result['lifecycle_status'],
                                         packaging=data_result['package'],
                                         pack_quantity=data_result['pack_quantity'],
                                         description=data_result['description'],
                                         )
        for pb in data_result['price_breaks']:
            SupplierPriceBreak.objects.create(part=sp, quantity=pb['Quantity'], price=pb['Price'], price_currency=pb['Currency'])
        print(f"[ADD_SUPPLIER_PART] Success! Created supplier part.")
        return JsonResponse({"message": "OK"})

# ---------------------------- import_full_part -------------------------------
    def import_full_part(self, request):
        """
        Import a complete part from supplier (Digikey/Mouser) including:
        - InvenTree part
        - Manufacturer company
        - Manufacturer part
        - Supplier part with price breaks
        - Part image
        """
        print(f"\n[IMPORT_FULL_PART] ========================================")
        try:
            data = json.loads(request.body)
            supplier_name = data.get('supplier', '').lower()
            sku = data.get('sku', '').strip()
            category_pk = data.get('category_pk')
            
            print(f"[IMPORT_FULL_PART] Supplier: {supplier_name}, SKU: {sku}, Category PK: {category_pk}")
            
            # Validation
            if not supplier_name or not sku or not category_pk:
                return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
            
            # Map supplier name to PK
            supplier_map = {
                'digikey': self.get_setting('DIGIKEY_PK'),
                'mouser': self.get_setting('MOUSER_PK')
            }
            
            supplier_pk = supplier_map.get(supplier_name)
            if not supplier_pk:
                return JsonResponse({"status": "error", "message": f"Supplier '{supplier_name}' not configured"}, status=400)
            
            # Get supplier company
            try:
                supplier_company = Company.objects.get(pk=supplier_pk)
                print(f"[IMPORT_FULL_PART] Supplier company: {supplier_company.name}")
            except Company.DoesNotExist:
                return JsonResponse({"status": "error", "message": f"Supplier company with PK {supplier_pk} not found"}, status=404)
            
            # Fetch extended part data from supplier API
            print(f"[IMPORT_FULL_PART] Fetching extended part data from {supplier_name}...")
            if supplier_name == 'digikey':
                from inventree_supplier_panel.digikey import Digikey
                part_data = Digikey.get_digikey_partdata_extended(self, sku, 'exact')
            elif supplier_name == 'mouser':
                from inventree_supplier_panel.mouser import Mouser
                part_data = Mouser.get_mouser_partdata_extended(self, sku, 'exact')
            else:
                return JsonResponse({"status": "error", "message": f"Unsupported supplier: {supplier_name}"}, status=400)
            
            # Check API result
            if part_data.get('error_status') != 'OK':
                return JsonResponse({"status": "error", "message": f"API Error: {part_data.get('error_status')}"}, status=500)
            
            if part_data.get('number_of_results', 0) == 0:
                return JsonResponse({"status": "error", "message": "Part not found in supplier database"}, status=404)
            
            print(f"[IMPORT_FULL_PART] ✓ Part data fetched successfully")
            print(f"[IMPORT_FULL_PART] MPN: {part_data.get('MPN')}, Manufacturer: {part_data.get('manufacturer_name')}")
            
            # Step 1: Create or find manufacturer company
            manufacturer_name = part_data.get('manufacturer_name')
            if not manufacturer_name:
                return JsonResponse({"status": "error", "message": "No manufacturer name in API response"}, status=500)
            
            manufacturer, created = Company.objects.get_or_create(
                name=manufacturer_name,
                is_manufacturer=True,
                defaults={'description': f'Manufacturer {manufacturer_name}'}
            )
            print(f"[IMPORT_FULL_PART] Manufacturer: {'Created' if created else 'Found'} - {manufacturer.name} (PK: {manufacturer.pk})")
            
            # Step 2: Create or update InvenTree part (use MPN as name)
            part_name = part_data.get('MPN', sku)
            
            # Check if part already exists
            existing_part = Part.objects.filter(name=part_name).first()
            if existing_part:
                print(f"[IMPORT_FULL_PART] Part '{part_name}' already exists (PK: {existing_part.pk}) - UPDATING")
                inv_part = existing_part
                
                # Update description if it's different
                new_description = part_data.get('description', '')[:250]
                if inv_part.description != new_description:
                    inv_part.description = new_description
                    inv_part.save()
                    print(f"[IMPORT_FULL_PART] ✓ Updated description")
                
                # Use existing part for subsequent operations
                print(f"[IMPORT_FULL_PART] Using existing part: {inv_part.name} (PK: {inv_part.pk})")
            else:
                # Create new part
                inv_part = Part.objects.create(
                    name=part_name,
                    description=part_data.get('description', '')[:250],  # Limit to 250 chars
                    category_id=category_pk,
                    active=True,
                    virtual=False,
                    component=True,
                    purchaseable=True
                )
                print(f"[IMPORT_FULL_PART] ✓ Created InvenTree part: {inv_part.name} (PK: {inv_part.pk})")
            
            # Step 3: Create or find manufacturer part
            mpn = part_data.get('MPN', '')
            mfg_part = ManufacturerPart.objects.filter(
                part=inv_part,
                manufacturer=manufacturer,
                MPN=mpn
            ).first()
            
            if not mfg_part:
                mfg_part = ManufacturerPart.objects.create(
                    part=inv_part,
                    manufacturer=manufacturer,
                    MPN=mpn
                )
                print(f"[IMPORT_FULL_PART] ✓ Created manufacturer part: {mpn} (PK: {mfg_part.pk})")
            else:
                print(f"[IMPORT_FULL_PART] Using existing manufacturer part: {mpn} (PK: {mfg_part.pk})")
            
            # Step 4: Create or find supplier part
            supplier_part = SupplierPart.objects.filter(
                part=inv_part,
                supplier=supplier_company,
                SKU=part_data.get('SKU', sku)
            ).first()
            
            if not supplier_part:
                supplier_part = SupplierPart.objects.create(
                    part=inv_part,
                    supplier=supplier_company,
                    manufacturer_part=mfg_part,
                    SKU=part_data.get('SKU', sku),
                    link=part_data.get('URL', ''),
                    note=part_data.get('lifecycle_status', ''),
                    packaging=part_data.get('package', ''),
                    pack_quantity=part_data.get('pack_quantity', '1'),
                    description=part_data.get('description', '')[:250]
                )
                print(f"[IMPORT_FULL_PART] ✓ Created supplier part: {supplier_part.SKU} (PK: {supplier_part.pk})")
            else:
                # Update supplier part details
                supplier_part.link = part_data.get('URL', '')
                supplier_part.note = part_data.get('lifecycle_status', '')
                supplier_part.packaging = part_data.get('package', '')
                supplier_part.pack_quantity = part_data.get('pack_quantity', '1')
                supplier_part.description = part_data.get('description', '')[:250]
                supplier_part.save()
                print(f"[IMPORT_FULL_PART] ✓ Updated supplier part: {supplier_part.SKU} (PK: {supplier_part.pk})")
            
            # Step 5: Create price breaks
            for pb in part_data.get('price_breaks', []):
                SupplierPriceBreak.objects.create(
                    part=supplier_part,
                    quantity=pb['Quantity'],
                    price=pb['Price'],
                    price_currency=pb.get('Currency', 'USD')
                )
            print(f"[IMPORT_FULL_PART] ✓ Created {len(part_data.get('price_breaks', []))} price breaks")
            
            # Step 6: Upload part image (only if part doesn't have one)
            image_url = part_data.get('primary_photo') or part_data.get('image_url')
            print(f"[IMPORT_FULL_PART] Image URL from API: {image_url}")
            
            # Check if part already has an image
            if inv_part.image and inv_part.image.name:
                print(f"[IMPORT_FULL_PART] Part already has image: {inv_part.image.name}, skipping upload")
            elif image_url:
                print(f"[IMPORT_FULL_PART] Downloading and uploading image from: {image_url[:100]}...")
                try:
                    from inventree_supplier_panel.image_manager import ImageManager
                    print(f"[IMPORT_FULL_PART] Calling ImageManager.get_image()...")
                    img_file = ImageManager.get_image(image_url)
                    print(f"[IMPORT_FULL_PART] ImageManager returned: {img_file}")
                    if img_file:
                        import os
                        file_size = os.path.getsize(img_file) if os.path.exists(img_file) else 0
                        print(f"[IMPORT_FULL_PART] Downloaded image file size: {file_size} bytes")
                        # Upload image using Django's file upload
                        with open(img_file, 'rb') as f:
                            from django.core.files import File
                            print(f"[IMPORT_FULL_PART] Saving image to part.image...")
                            inv_part.image.save(f'part_{inv_part.pk}.jpg', File(f), save=True)
                        print(f"[IMPORT_FULL_PART] ✓ Image uploaded successfully to part {inv_part.pk}")
                        ImageManager.clean_cache()
                    else:
                        print(f"[IMPORT_FULL_PART] ✗ Image download failed - ImageManager returned None")
                except Exception as e:
                    print(f"[IMPORT_FULL_PART] ✗ Image upload error: {e}")
                    import traceback
                    traceback.print_exc()
                    # Don't fail the whole import if image fails
            else:
                print(f"[IMPORT_FULL_PART] No image URL available from supplier API")
            
            # Step 7: Import parameters
            parameters = part_data.get('parameters', [])
            print(f"[IMPORT_FULL_PART] Found {len(parameters)} parameters from API")
            if parameters:
                # Load parameter mapping from settings
                try:
                    param_map_json = self.get_setting('DIGIKEY_PARAMETER_MAP')
                    param_map = json.loads(param_map_json) if param_map_json else {}
                    print(f"[IMPORT_FULL_PART] Loaded parameter map with {len(param_map)} mappings")
                except Exception as e:
                    print(f"[IMPORT_FULL_PART] ✗ Error loading parameter map: {e}, using empty map")
                    param_map = {}
                
                params_created = 0
                for param in parameters:
                    param_name = param.get('name', '')
                    param_value = param.get('value', '')
                    
                    if not param_name or not param_value:
                        continue
                    
                    # Map parameter name using configuration
                    mapped_name = param_map.get(param_name, param_name)
                    print(f"[IMPORT_FULL_PART] Processing parameter: '{param_name}' -> '{mapped_name}' = '{param_value}'")
                    
                    try:
                        # Get or create PartParameterTemplate
                        template, created = PartParameterTemplate.objects.get_or_create(
                            name=mapped_name,
                            defaults={'description': f'Parameter {mapped_name}'}
                        )
                        if created:
                            print(f"[IMPORT_FULL_PART]   Created new template: {mapped_name}")
                        
                        # Create PartParameter for this part
                        part_param, created = PartParameter.objects.get_or_create(
                            part=inv_part,
                            template=template,
                            defaults={'data': param_value}
                        )
                        if created:
                            params_created += 1
                            print(f"[IMPORT_FULL_PART]   ✓ Created parameter: {mapped_name} = {param_value}")
                        else:
                            print(f"[IMPORT_FULL_PART]   Parameter already exists: {mapped_name}")
                    except Exception as e:
                        print(f"[IMPORT_FULL_PART]   ✗ Error creating parameter {mapped_name}: {e}")
                
                print(f"[IMPORT_FULL_PART] ✓ Created {params_created} new parameters")
            
            # Step 8: Import HTSUS code if enabled
            if self.get_setting('IMPORT_HTSUS'):
                htsus_code = part_data.get('htsus', '')
                if htsus_code:
                    print(f"[IMPORT_FULL_PART] Importing HTSUS code: {htsus_code}")
                    try:
                        # Get or create HTSUS parameter template
                        htsus_template, created = PartParameterTemplate.objects.get_or_create(
                            name='HTSUS',
                            defaults={'description': 'Harmonized Tariff Schedule code'}
                        )
                        # Create or update HTSUS parameter
                        htsus_param, created = PartParameter.objects.update_or_create(
                            part=inv_part,
                            template=htsus_template,
                            defaults={'data': htsus_code}
                        )
                        if created:
                            print(f"[IMPORT_FULL_PART] ✓ Created HTSUS parameter: {htsus_code}")
                        else:
                            print(f"[IMPORT_FULL_PART] ✓ Updated HTSUS parameter: {htsus_code}")
                    except Exception as e:
                        print(f"[IMPORT_FULL_PART] ✗ Error importing HTSUS: {e}")
                else:
                    print(f"[IMPORT_FULL_PART] No HTSUS code available from API")
            
            print(f"[IMPORT_FULL_PART] ========================================")
            print(f"[IMPORT_FULL_PART] ✓✓✓ SUCCESS - Part imported completely!")
            
            # Return success response
            return JsonResponse({
                "status": "success",
                "message": "Part imported successfully",
                "part_pk": inv_part.pk,
                "part_name": inv_part.name,
                "manufacturer_name": manufacturer.name,
                "mpn": mpn,
                "supplier_name": supplier_company.name,
                "sku": supplier_part.SKU,
                "description": part_data.get('description', '')[:100]
            })
            
        except json.JSONDecodeError as e:
            print(f"[IMPORT_FULL_PART] ✗ JSON decode error: {e}")
            return JsonResponse({"status": "error", "message": "Invalid JSON in request"}, status=400)
        except Part.DoesNotExist:
            print(f"[IMPORT_FULL_PART] ✗ Category not found")
            return JsonResponse({"status": "error", "message": "Invalid category PK"}, status=404)
        except Exception as e:
            print(f"[IMPORT_FULL_PART] ✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": f"Internal error: {str(e)}"}, status=500)

# ---------------------------- Define the suppliers ----------------------------
    registered_suppliers = {'Mouser': {'pk': 0,
                                       'name': 'Mouser',
                                       'po_template': 'supplier_panel/mouser.html',
                                       'is_registered': False,
                                       'get_partdata': Mouser.get_mouser_partdata,
                                       'update_cart': Mouser.update_mouser_cart,
                                       'create_cart': Mouser.create_mouser_cart,
                                       },
                            'Digikey': {'pk': 0,
                                        'name': 'Digikey',
                                        'po_template': 'supplier_panel/mouser.html',
                                        'is_registered': False,
                                        'get_partdata': Digikey.get_digikey_partdata_v4,
                                        'update_cart': Digikey.update_digikey_cart,
                                        'create_cart': Digikey.create_digikey_cart,
                                        },
                            'Farnell': {'pk': 0,
                                        'name': 'Farnell',
                                        'po_template': 'supplier_panel/mouser.html',
                                        'is_registered': False,
                                        'get_partdata': Farnell.get_farnell_partdata,
                                        'update_cart': '',
                                        'create_cart': Farnell.create_farnell_cart,
                                        }
                            }
