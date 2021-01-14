from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ElementTree
import base64

import requests
import os.path
import datetime


""" 
    PrestaRequest main class for monitoring and actualization products barcode and QR.
    Class contains standart methods for works with PrestaShop API.
    Require lib: xml.etree, requests.
"""

class PrestaRequest:
    
    """ Constructor takes follow parametrs:
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


    # Private methods here ++++++++++++++++++++++++++++++++


    def _xml_data_extractor(self, data, tag=None, **kwargs):
        
        if tag == None:
            kwargs_dict = kwargs.get('kwargs')
        
        try:
            xml_content = ET.fromstring(data.content)  # Create ET instanse and root tag
            general_tag = xml_content[0]  # Get prestashop tag
            tag = general_tag.find(kwargs_dict.get('tag'))
            tag_inner_link = tag.get('{http://www.w3.org/1999/xlink}href')

            return tag_inner_link

        except:
            return None


    def _loging(self, **kwargs):
        kwargs = kwargs.get('kwargs')

        # Check file
        if not os.path.exists(os.path.join(self.base_dir, 'log/log.txt')):
            f = open(os.path.join(self.base_dir, 'log/log.txt'), "w")
            f.close()

        # if exists
        try:
            for i in kwargs.items():
                writable_data = "{}: {}".format(datetime.datetime.now(), i)

                with open(os.path.join(self.base_dir, 'log/log.txt'), "a", encoding="UTF-8") as f:
                    print(writable_data, file=f)
        except Exception as e:
            return e
    
    
    # Private methods here ++++++++++++++++++++++++++++++++


    def get_combination_url(self):

        get_combination_xml = requests.get(
            self.request_url, auth=(self.api_secret_key, ''))

        if get_combination_xml.status_code == 200:
            try:
                request_data = {'tag': 'combination'}
                self.get_combination_link = self._xml_data_extractor(
                    data=get_combination_xml,
                    kwargs=request_data)
                
                if self.get_combination_link != None:

                    return self.get_combination_link

            except:
                return None

    
    # Get product link from combination page
    def get_product_url(self, request_url=None):
        
        if request_url == None:
            get_combination_link = self.get_combination_url()
        
        if get_combination_link:

            get_product_link_from_comb = requests.get(get_combination_link, auth=(self.api_secret_key, ''))

            if get_product_link_from_comb.status_code == 200:
                request_data = {'tag': 'id_product'}
                product_url = self._xml_data_extractor(
                    data=get_product_link_from_comb,
                    kwargs=request_data)
                
                if product_url != None:
                    return product_url
                
            else:
                return get_product_link_from_comb.status_code
        
        else:
            return "Product does not exist: {}".format(request_url)


    def get_product_stocks_url(self, request_url=None):
        
        if request_url != None:
            get_product_link = request_url
        else:
            get_product_link = self.get_product_url()

        stock_data = []

        # Stock finding
        if get_product_link:
            product_page = requests.get(get_product_link, auth=(self.api_secret_key, ''))

            if product_page.status_code == 200:

                xml_content = ET.fromstring(product_page.content)
                general_tag = xml_content[0].find('associations')
                get_stock_tag = general_tag.find('stock_availables')

                for i in get_stock_tag.findall('stock_available'):
                    stock_data.append(i.get('{http://www.w3.org/1999/xlink}href'))
                
                return stock_data
            else:
                return product_page.status_code

        else:
            return None


    def stock_parser(self, stock_list=None):

        if stock_list == None:
            stock_list = self.get_product_stocks_url()

        if len(stock_list) != 0:

            # Stock parsing
            for i in stock_list:
                stock_page = requests.get(i, auth=(self.api_secret_key, ''))
                
                if stock_page.status_code == 200:
                    xml_content = ET.fromstring(stock_page.content)
                    self.quantity = xml_content[0].find('quantity').text
                    combination_link = xml_content[0].find('id_product_attribute')
                    id_product = xml_content[0].find('id_product').text

                    print(self.get_combination_link, " / ", combination_link.get('{http://www.w3.org/1999/xlink}href'))

                    if self.get_combination_link == combination_link.get('{http://www.w3.org/1999/xlink}href'):
                        self.stock_url = str(i)
                        print("Product with id {} will be delete! Total quantity: {}".format(id_product, self.quantity))

                        if self.xml_response_create(new_quantity=int(self.quantity) - 1):
                            return(int(self.quantity) - 1)
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
            'Authorization': 'Basic ' + self.api_secret_key_64,
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0',
            'referer': 'https://3gravity.pl/',
        }
        
        update_stocks = requests.put(request_url, headers=headers, data=response_data)

        if update_stocks.status_code == 200:
            return "All data has been updated!"
        
        else:
            print(update_stocks.status_code)
            return update_stocks.content


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
                        return link
                    

        
        else:
            raise TypeError()


    # The func try to find stock url from urlpattern: ['https://3gravity.pl/api/stocks/?filter[reference]=KRHT..']
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

                if len(get_stock_url) > 1:
                    for i in get_stock_url:
                        response_data.append(i.get('{http://www.w3.org/1999/xlink}href'))
                    
                    return self._wd(warehouse=warehouse, data=response_data)

            except:
                return "Product does not exist!"

        else:
            return get_stock_content.status_code


    def warehouse_quantity_mgmt(self, warehouse, reference, delete=True, request_url=None):
        if request_url == None:
            request_url = self.stock_control(warehouse=warehouse, reference=reference)

        if not delete:
            mgmt_var = 1
        
        else:
            mgmt_var = -1
        
        
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
            get_physical_quantity.text = str(int(get_physical_quantity.text) + mgmt_var)
            get_usable_quantity.text = str(int(get_usable_quantity.text) + mgmt_var)
            
            # Remove not filterable field for PUT request
            get_not_filterable_fields = general_product.find('real_quantity')
            general_product.remove(get_not_filterable_fields)

            
            # Write global_quantity for controlling summary quantity
            self.global_quantity = [get_physical_quantity.text, get_usable_quantity.text]


            # Convert element object in ElementTree
            format_xml_tree = ElementTree(xml_content)

            # Write XML for PUT request
            format_xml_tree.write(os.path.join(self.base_dir, 'temp/log.xml'))

            # with open(os.path.join(log_path, 'temp/log.xml')) as file:
            #     data = file.read()

            data = {
                'global_quantity': self.global_quantity,
            }

            self._loging(kwargs=data)

            return True

        else:
            return None



#  'stocks' => array('description' => 'Stocks', 'class' => 'Stock', 'forbidden_method' => array('PUT', 'POST', 'DELETE')),