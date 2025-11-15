from django.http import HttpResponse
from django.http import JsonResponse
from django.urls import re_path

from order.api import PurchaseOrderDetail
from order.models import PurchaseOrder
from part.api import PartDetail
from part.models import Part
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

    def get_ui_features(self, feature_type, **kwargs):
        """Return UI features such as navigation items."""
        if feature_type == 'navigation':
            return [{
                'key': 'import-parts',
                'title': 'Import Parts',
                'icon': 'ti:package-import:outline',
                'source': self.plugin_static_file('import_parts_ui.js:renderImportPartsPage')
            }]
        return []

    def get_ui_panels(self, request, context, **kwargs):
        """Return custom panels for Purchase Orders and Parts."""
        panels = []
        target_model = context.get('target_model')
        target_id = context.get('target_id')

        # Load registered suppliers from settings
        self._load_registered_suppliers()

        # For Purchase Orders: PO transfer panels
        if target_model == 'purchaseorder' and target_id:
            # Check permissions
            has_permission = (
                check_user_role(request.user, 'purchase_order', 'change') or
                check_user_role(request.user, 'purchase_order', 'delete') or
                check_user_role(request.user, 'purchase_order', 'add')
            )

            if not has_permission:
                return panels

            # Get the PO and check supplier
            try:
                po = PurchaseOrder.objects.get(pk=target_id)
            except PurchaseOrder.DoesNotExist:
                return panels

            # Add panel for Digikey supplier
            if (self.registered_suppliers.get('Digikey', {}).get('is_registered') and
                po.supplier.pk == self.registered_suppliers['Digikey']['pk']):
                panels.append({
                    'key': 'digikey-po-transfer',
                    'title': 'Digikey Actions',
                    'icon': 'ti:shopping-cart:outline',
                    'source': self.plugin_static_file('po_transfer_panel.js:renderDigikeyPanel'),
                    'context': {
                        'po_pk': target_id,
                        'supplier': 'Digikey'
                    }
                })

            # Add panel for Mouser supplier
            if (self.registered_suppliers.get('Mouser', {}).get('is_registered') and
                po.supplier.pk == self.registered_suppliers['Mouser']['pk']):
                panels.append({
                    'key': 'mouser-po-transfer',
                    'title': 'Mouser Actions',
                    'icon': 'ti:shopping-cart:outline',
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
            
            # Step 2: Create InvenTree part (use MPN as name)
            part_name = part_data.get('MPN', sku)
            
            # Check if part already exists
            existing_part = Part.objects.filter(name=part_name).first()
            if existing_part:
                print(f"[IMPORT_FULL_PART] ✗ Part '{part_name}' already exists (PK: {existing_part.pk})")
                return JsonResponse({
                    "status": "error",
                    "message": f"Part '{part_name}' already exists in InvenTree",
                    "part_pk": existing_part.pk
                }, status=409)
            
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
            
            # Step 3: Create manufacturer part
            mpn = part_data.get('MPN', '')
            mfg_part = ManufacturerPart.objects.create(
                part=inv_part,
                manufacturer=manufacturer,
                MPN=mpn
            )
            print(f"[IMPORT_FULL_PART] ✓ Created manufacturer part: {mpn} (PK: {mfg_part.pk})")
            
            # Step 4: Create supplier part
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
            
            # Step 5: Create price breaks
            for pb in part_data.get('price_breaks', []):
                SupplierPriceBreak.objects.create(
                    part=supplier_part,
                    quantity=pb['Quantity'],
                    price=pb['Price'],
                    price_currency=pb.get('Currency', 'USD')
                )
            print(f"[IMPORT_FULL_PART] ✓ Created {len(part_data.get('price_breaks', []))} price breaks")
            
            # Step 6: Upload part image
            image_url = part_data.get('primary_photo') or part_data.get('image_url')
            if image_url:
                print(f"[IMPORT_FULL_PART] Downloading and uploading image...")
                try:
                    from inventree_supplier_panel.image_manager import ImageManager
                    img_file = ImageManager.get_image(image_url)
                    if img_file:
                        # Upload image using Django's file upload
                        with open(img_file, 'rb') as f:
                            from django.core.files import File
                            inv_part.image.save(f'part_{inv_part.pk}.jpg', File(f), save=True)
                        print(f"[IMPORT_FULL_PART] ✓ Image uploaded successfully")
                        ImageManager.clean_cache()
                    else:
                        print(f"[IMPORT_FULL_PART] ✗ Image download failed")
                except Exception as e:
                    print(f"[IMPORT_FULL_PART] ✗ Image upload error: {e}")
                    # Don't fail the whole import if image fails
            
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
