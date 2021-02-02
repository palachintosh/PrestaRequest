from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ElementTree
import base64

import requests
import os.path
import datetime


""" 
    PrestaRequest main class for monitoring and actualization products barcode and QR.
    Class contains standart methods for works with PrestaShop API.
    Requirements: xml.etree, requests.
"""

class PrestaRequest:
    
    """ 
        Constructor takes follow parametrs:
        request_url: link of product that you want to change,
        new_text_value: the value you want to set up,
    """

    def __init__(self, api_secret_key, request_url=None, **kwargs):
        
        try:
            self.api_secret_key = str(api_secret_key) #!API key is necessary!
            self.api_secret_key_64 = base64.b64encode((self.api_secret_key + ':').encode())

        except:
            raise TypeError('The secret_key must be a string!')
        
        # Main path to working directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.request_url = request_url
        self.kwargs = kwargs.items()

        #product meta to return
        self.name = None
        self.total_quantity = None
        self.w_from = None
        self.w_to = None
        self.date = str(datetime.datetime.now().strftime("%d-%m-%Y, %H:%M"))


    # Private methods here ++++++++++++++++++++++++++++++++


    def _xml_data_extractor(self, data, tag=None, **kwargs):
        if tag == None:
            kwargs_dict = kwargs.get('kwargs')
            tag = kwargs_dict.get('tag')

        try:
            xml_content = ET.fromstring(data.content)  # Create ET instanse and root tag
            general_tag = xml_content[0]  # Get prestashop tag
            tag = general_tag.find(tag)
            tag_inner_link = tag.get('{http://www.w3.org/1999/xlink}href')

            # return tag_inner_link
            product_meta = {
                'product_link': tag_inner_link
            }
            return product_meta

        except:
            return None


    def _logging(self, **kwargs):
        kwargs = kwargs.get('kwargs')

        if kwargs.get('name') != None:
            name = kwargs.pop('name')
        else:
            name = "log.txt"


        # Check file
        if not os.path.exists(os.path.join(self.base_dir, 'log/' + name)):
            f = open(os.path.join(self.base_dir, 'log/' + name), "w")
            f.close()

        # if exists
        try:
            for i in kwargs.items():
                writable_data = "{}: {}".format(datetime.datetime.now(), i)

                with open(os.path.join(self.base_dir, 'log/' + name), "a", encoding="UTF-8") as f:
                    print(writable_data, file=f)
        except Exception as e:
            return e
    

    #warehouse_detect
    def _wd(self, warehouse, data):

        warehouses = {
            'shop': '4',
            'x': '5',
            'y': '6'
        }

        if type(data) == list:
            for link in data:
                get_warehouse_id = requests.get(str(link), auth=(self.api_secret_key, ''))
                
                if get_warehouse_id.status_code == 200:
                    xml_content = ET.fromstring(get_warehouse_id.content)
                    general_product = xml_content[0]
                    w_id = general_product.find('id_warehouse').text

                    if w_id == warehouses.get(warehouse.lower()):
                        self.warehouse_stock_link = link
                        
                        return self.warehouse_stock_link

        else:
            raise TypeError()


    # Private methods here ++++++++++++++++++++++++++++++++


    def get_combination_url(self):

        get_combination_xml = requests.get(
            self.request_url, auth=(self.api_secret_key, ''))

        if get_combination_xml.status_code == 200:
            try:
                request_data = {'tag': 'combination'}
                get_combination_data = self._xml_data_extractor(
                    data=get_combination_xml,
                    kwargs=request_data)
                self.get_combination_link = get_combination_data.get('product_link')
                print(self.get_combination_link)
                
                if self.get_combination_link != None:

                    return self.get_combination_link

            except:
                return None

    
    # Get product link from combination page
    def get_product_url(self, request_url=None):
        
        if request_url == None:
            get_combination_link = self.get_combination_url()
        else:
            get_combination_link = request_url
        
        if get_combination_link:

            get_product_link_from_comb = requests.get(get_combination_link, auth=(self.api_secret_key, ''))

            if get_product_link_from_comb.status_code == 200:
                request_data = {'tag': 'id_product'}
                product_url = self._xml_data_extractor(
                    data=get_product_link_from_comb,
                    kwargs=request_data)
                
                if product_url != None:
                    return product_url.get('product_link')
                
            else:
                return get_product_link_from_comb.status_code
        
        else:
            return {'error': 'Product does not exit in the stocks!'}


    def get_product_stocks_url(self, request_url=None):
        
        # If request_url eq. None - get request_url from get_product_url
        get_product_link = request_url
        
        if request_url == None:
            get_product_link = self.get_product_url()
            try:
                str(get_product_link)
            except:
                get_product_link.get('error')
                response_data = {
                    'error': get_product_link.get('error')
                }
                
                return response_data


        stock_data = []

        # Stock finding
        if type(get_product_link) is str:
            product_page = requests.get(get_product_link, auth=(self.api_secret_key, ''))

            if product_page.status_code == 200:

                # In product page stock_availables is in 'associatins' block 
                xml_content = ET.fromstring(product_page.content)
                # Get general tag for stock_availables
                general_tag = xml_content[0].find('associations')
                # Get stock_availables tag directly
                get_stock_tag = general_tag.find('stock_availables')

                # Try to find all tags inside stock_availables and
                # extract each node link
                for i in get_stock_tag.findall('stock_available'):
                    stock_data.append(i.get('{http://www.w3.org/1999/xlink}href'))
                
                name = xml_content[0].find('name')
                self.name = name.find('language').text

                product_data = {
                    'name': self.name,
                    'date': self.date,
                    'stock_data': stock_data
                }


                # Return list with links if all right
                # return stock_data
                return product_data

            else:
                #return status code if code another than 200
                return product_page.status_code

        # Return None if request failed
        else:
            return None


    def stock_parser(self, quantity_to_transfer, delete=True, stock_list=None):

        # Check if stock_list has anything
        # If not - get stock link from func
        if stock_list == None:
            stock_list = self.get_product_stocks_url()
            if stock_list != None:
                stock_list = stock_list.get('stock_data')
            else:
                return None
            
        
        # If true, than increment quantity
        if not delete:
            mgmt_var = quantity_to_transfer
        else:
            mgmt_var = -1

        if len(stock_list) != 0:

            # Stocks parsing
            for i in stock_list:
                stock_page = requests.get(i, auth=(self.api_secret_key, ''))
                
                if stock_page.status_code == 200:
                    xml_content = ET.fromstring(stock_page.content)

                    # Get total quantity from stock_availables
                    self.quantity = xml_content[0].find('quantity').text
                    print("QUANTITY: ", self.quantity)
                    # Get product atribute
                    combination_link = xml_content[0].find('id_product_attribute')
                    # Get product id
                    id_product = xml_content[0].find('id_product').text

                    print(self.get_combination_link, " / ", combination_link.get('{http://www.w3.org/1999/xlink}href'))

                    # Varify product
                    # If global combination link and combination link from product card are eq.
                    # Than write global self.stock_url for future PUT request
                    # and decrease general quantity
                    if self.get_combination_link == combination_link.get('{http://www.w3.org/1999/xlink}href'):
                        self.stock_url = str(i)
                        print("Product with id {} will be delete! Total quantity: {}".format(id_product, self.quantity))

                        if self.xml_response_create(new_quantity=int(self.quantity) + mgmt_var):
                            return(int(self.quantity) + mgmt_var)
                    else:
                        print("Product id: {}.".format(id_product), int(self.quantity), combination_link)
                else:
                    return stock_page.status_code
        else:
            return None


    def xml_response_create(self, new_quantity):
        try:
            get_stock_xml = requests.get(self.stock_url, auth=(self.api_secret_key, ''))
            
            xml_content = ET.fromstring(get_stock_xml.content)  # Create ET instanse and root tag
            general_tag = xml_content[0]  # Get prestashop tag
            tag = general_tag.find('quantity')

            tag.text = str(new_quantity)
            tag.set('update', 'yes')

            format_xml_tree = ElementTree(xml_content)
            format_xml_tree.write(os.path.join(self.base_dir, 'temp/log.xml'))

            return True
        except:
            return 'XML writing error!'


    def presta_put(self, response_data=None, request_url=None):

        if request_url == None:
            request_url = self.stock_url
        
        if response_data == None:
            try:
                with open(os.path.join(self.base_dir, 'temp/log.xml')) as file:
                    response_data = file.read()
            except FileNotFoundError as e:
                return e

        headers = {
            'Authorization': 'Basic ' + self.api_secret_key_64.decode(),
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0',
            'referer': 'https://3gravity.pl/',
        }
        
        update_stocks = requests.put(request_url, headers=headers, data=response_data)

        if update_stocks.status_code == 200:
            return {'success': 'All data has been updated!'}
        
        else:
            print(update_stocks.status_code)
            return {'error': update_stocks.status_code}


    # The func try to find stock url from urlpattern: ['https://domain.com/api/stocks/?filter[reference]=KRHT..']
    # in warehouses
    # and return the stock link if product exists
    # or "Product does not exist!" str if not.
    # Return status_code another than 200 if something goes wrong.

    def stock_control(self, reference, warehouse, request_url=None):
        if request_url == None:
            request_url = 'https://3gravity.pl/api/stocks/?filter[reference]={}'.format(reference)
        
        get_stock_content = requests.get(request_url, auth=(self.api_secret_key, ''))

        if get_stock_content.status_code == 200:
            try:
                xml_content = ET.fromstring(get_stock_content.content)
                general_product = xml_content[0]
                get_stock_url = general_product.findall('stock')
                response_data = []

                if len(get_stock_url) >= 1:
                    for i in get_stock_url:
                        response_data.append(i.get('{http://www.w3.org/1999/xlink}href'))
                    
                    return self._wd(warehouse=warehouse, data=response_data)

            except:
                return "Product does not exist!"

        else:
            return get_stock_content.status_code


    def warehouse_quantity_mgmt(self, warehouse, reference, quantity_to_transfer=None, delete=True, request_url=None):
        if request_url == None:
            request_url = self.stock_control(warehouse=warehouse, reference=reference)

            if request_url == "Product does not exist!":
                return {'error': request_url}
        # Add or delete product

        # if not delete:
        #     mgmt_var = 1

        # else:
        #     mgmt_var = -1
        

        if quantity_to_transfer == None and delete:
            mgmt_var = -1
            print("first_case", mgmt_var)

        elif quantity_to_transfer is not None and delete:
            mgmt_var =  0 - int(quantity_to_transfer)
            print("second_case", mgmt_var)

        elif quantity_to_transfer is not None and not delete:
            mgmt_var = int(quantity_to_transfer)
            print("third_case", mgmt_var)
        
        else:
            return None

        self.total_quantity = abs(mgmt_var)



        get_stocks_content = requests.get(request_url, auth=(self.api_secret_key, ''))

        if get_stocks_content.status_code == 200:
            # Make ET object from XML content from rqeuest
            xml_content = ET.fromstring(get_stocks_content.content)
            
            # Get general tag from API page. For example,  in "https://domain_name.com/api/stocks/1"
            # the first tag (in prestashop continer) will be 'stock'
            general_product = xml_content[0]

            # Get warehouse quantity and remove one
            get_physical_quantity = general_product.find('physical_quantity')
            get_usable_quantity = general_product.find('usable_quantity')

            if (int(get_physical_quantity.text) + mgmt_var) >= 0:

                get_physical_quantity.text = str(int(get_physical_quantity.text) + mgmt_var)
                get_usable_quantity.text = str(int(get_usable_quantity.text) + mgmt_var)

            else:
                return {'error': 'Unable to delete products! Total quantity is less than 0.'}
            

            # Remove not filterable field for PUT request
            get_not_filterable_fields = general_product.find('real_quantity')
            general_product.remove(get_not_filterable_fields)

            
            # Write global_quantity for controlling summary quantity
            self.global_quantity = [int(get_physical_quantity.text), int(get_usable_quantity.text)]


            # Convert element object in ElementTree
            format_xml_tree = ElementTree(xml_content)

            # Write XML for PUT request
            format_xml_tree.write(os.path.join(self.base_dir, 'temp/log.xml'))

            data = {
                'name': 'log.txt',
                'PQ': get_physical_quantity.text,
                'UQ': get_usable_quantity.text,
                'RQ': get_not_filterable_fields.text
            }

            self._logging(kwargs=data)
            return request_url

        else:
            return None


    # Return phisical and usable quantity of product
    def _warehouse_q_get(self, request_url):
        get_stocks_content = requests.get(request_url, auth=(self.api_secret_key, ''))

        if get_stocks_content.status_code == 200:
            # Make ET object from XML content from rqeuest
            xml_content = ET.fromstring(get_stocks_content.content)
            general_product = xml_content[0]

            get_physical_quantity = int(general_product.find('physical_quantity').text)
            get_usable_quantity = int(general_product.find('usable_quantity').text)
            get_real_q = int(general_product.find('real_quantity').text)
     
            # Write global_quantity for controlling summary quantity
            self.global_quantity = [get_physical_quantity, get_usable_quantity]

            data = {
                'name': 'transfer_log.txt',
                'PQ': get_physical_quantity,
                'UQ': get_usable_quantity,
                'RQ': get_real_q
            }

            self._logging(kwargs=data)
            return request_url

        else:
            return None


    # Method for products transferring
    def product_transfer(self, quantity_to_transfer, w_from, w_to, code, request_url=None):
        
        request_url_from = self.stock_control(warehouse=w_from, reference=code)
        request_url_to = self.stock_control(warehouse=w_to, reference=code)

        if request_url_from and request_url_to:
            get_from_q = self.warehouse_quantity_mgmt(
                warehouse=None,
                quantity_to_transfer=quantity_to_transfer,
                reference=None,
                request_url=request_url_from)

            if type(get_from_q) is dict:
                if get_from_q.get('error'):
                    return get_from_q

            # if get_from_q != None and self.global_quantity[0] - quantity_to_transfer >= 0:
            if get_from_q != None:
                
                # Make a put request!
                update_quantity = self.presta_put(request_url=get_from_q)
                # update_quantity = {'success': '-'}

                if update_quantity.get('success') != None:
                    
                    # Update 'TO' warehouse
                    get_to_q = self.warehouse_quantity_mgmt(
                        quantity_to_transfer=quantity_to_transfer,
                        warehouse=w_to,
                        reference=None,
                        delete=False,
                        request_url=request_url_to)

                    if get_to_q != None:
                        # update_quantity = {'success': '-'}
                        update_quantity = self.presta_put(request_url=get_to_q)

                        if update_quantity.get('success') != None:
                            self.w_from = w_from
                            self.w_to = w_to

                            response_data = {
                                'success': 'YES',
                                'name': self.name,
                                'quantity': self.total_quantity,
                                'w_from': self.w_from,
                                'w_to': self.w_to,
                                'date': self.date
                            }
                            return response_data

        else:
            error_msg = 'Product with this code was not found on the stocks! From: {}, TO: {}'.format(w_from, w_to)
            
            return {'error': error_msg}



    def to_w_transfer(self, quantity_to_transfer, w_to, code):

        update_warehouse = None
        add_bikes = None
        self.request_url = 'https://3gravity.pl/api/combinations/?filter[reference]={}'.format(code)

        # Get link product on warehouse
        request_url_to = self.stock_control(warehouse=w_to, reference=code)
        
        stock_parser = self.stock_parser(
                                        quantity_to_transfer,
                                        delete=False)
        
        if stock_parser:
            add_bikes = self.presta_put()

            if request_url_to and add_bikes != None:
                get_to_q = self.warehouse_quantity_mgmt(
                    warehouse=None,
                    quantity_to_transfer=quantity_to_transfer,
                    reference=None,
                    request_url=request_url_to,
                    delete=False
                    )
                
                print(get_to_q)

                if get_to_q:
                    update_warehouse = self.presta_put(request_url=get_to_q)


        if add_bikes != None and update_warehouse != None:
            self.w_to = w_to
            
            response_data = {
                'success': 'YES',
                'name': str(self.name),
                'quantity': str(self.total_quantity),
                'w_from': str(self.w_from),
                'w_to': str(self.w_to),
                'date': str(self.date)
            }

            return response_data

        else:
            return {'error': 'Unable to mooving products!'}
