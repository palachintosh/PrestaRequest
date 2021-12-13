from json import load
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ElementTree
from .var import *
from string import ascii_letters, digits
import random
import json
import logging

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
    # Logger conf
    formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(message)s")
    logger_base_dir = os.path.dirname(os.path.abspath(__file__))


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
        

        # Product active stamp
        active_status = None
        self.warehouses = {
            'shop': '4',
            'x': '5',
            'y': '6'
        }

        # Restore token generate
        symbols =ascii_letters + digits
        rand = random.SystemRandom()
        self.restore_id = "".join(rand.choice(symbols) for i in range(8))


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
        if isinstance(data, list):
            for link in data:
                get_warehouse_id = requests.get(str(link), auth=(self.api_secret_key, ''))
                
                if get_warehouse_id.status_code == 200:
                    xml_content = ET.fromstring(get_warehouse_id.content)
                    general_product = xml_content[0]
                    w_id = general_product.find('id_warehouse').text

                    if w_id == self.warehouses.get(warehouse.lower()):
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

                
                if self.get_combination_link is not None:

                    return self.get_combination_link

            except:
                return None


    # Check combination default values, quantity
    # and find the highest value.
    # Than, setting up this to default
    def check_default_comb(self, stock_list):
        stock_values = []
        # Write log
        file_handler = logging.FileHandler(self.logger_base_dir + "/mainp/presta_logs/comb_check.log")
        logger = logging.getLogger('comb_check_log')
        logger.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.formatter)
        logger.addHandler(file_handler)
 

        for get_dc in stock_list:
            # Get request on stock_availables
            get_stock = requests.get(get_dc, auth=(self.api_secret_key, ''))

            if get_stock.status_code != 200:
                return False
            
            get_values = self.get_ps_xml_tag(
                "quantity", "id_product_attribute",
                content=get_stock.content,
                tag=None,
            )

            if get_values is None:
                return False

            else:
                if get_values.get('id_product_attribute') != '0':
                    stock_values.append(get_values)


        if len(stock_values) > 0:
            candidate = None
            default = None

            for i in stock_values:
                check_if_default = self.set_default_combination(
                        comb_id=i.get('id_product_attribute'),
                        value=""
                    )

                if not check_if_default and int(i.get('quantity')) > 0:
                    candidate = i.get('id_product_attribute')

                elif not check_if_default and int(i.get('quantity')) == 0:
                    continue

                elif check_if_default and int(i.get('quantity')) == 0:
                    default = i.get('id_product_attribute')

                else:
                    return True
                

            if candidate != default and ((not candidate is None) and (not default is None)):
                a = self.set_default_combination(comb_id=default, value="", check=False)
                b = self.set_default_combination(comb_id=candidate, value="1", check=False)

                # Logger
                logger.info(
                str(candidate) + "will be mark as \"default\", and " + str(default) + " will be unmarked.")
               
                return True

            elif candidate is None or default is None:
                return True
                
            else:
                return False
                
            
    # Get product link from combination page
    def get_product_url(self, request_url=None):
        
        if request_url is None:
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
                
                if product_url is not None:
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
    


    def get_ps_xml_tag(self, *args, content, tag, find_all=True):
        """
            DONT use "find_all" with "args".
            If "args" was given, finder will be try to find ONLY single value for each tag
        """
        tag_context = {}

        xml_content = ET.fromstring(content)
        main_tag = xml_content[0]

        
        if len(args) == 0:
            if find_all:
                return main_tag.findall(tag)

            else:
                return main_tag.find(tag)
        
        else:
            for tag in args:
                get_tag_context = main_tag.find(tag)

                if not get_tag_context is None: 
                    tag_context.update({
                        tag: get_tag_context.text
                    })
            
            return tag_context


    # Forms response for product_card with changed activity
    def activity_reponse(self, product, tag, value):
        try:
            xml_content = ET.fromstring(product)
            general_tag = xml_content[0]
            
            tag = general_tag.find(tag)
            tag.text = value

            # Not filterable delete
            not_filter_tags = []
            
            for not_filter in general_tag:
                if not_filter.get('notFilterable') == 'true':
                    not_filter_tags.append(not_filter)

            for i in not_filter_tags:
                general_tag.remove(i)
            
            format_xml_tree = ElementTree(xml_content)
            format_xml_tree.write(os.path.join(self.base_dir, 'temp/log.xml'))
            
            return True

        except:
            return False


    # Check if activity more than 0
    def product_active_check(self, product_id) -> bool:
        product_page = requests.get(MAIN_PRODUCTS_URL + product_id, auth=(self.api_secret_key, ''))

        if product_page.status_code == 200:
            activity = self.get_ps_xml_tag(
                content=product_page.content,
                tag="active",
                find_all=False)


            if activity.text == '1':
                return True


            else:
                activity_set = self.activity_reponse(
                    product=product_page.content,
                    tag="active",
                    value="1",
                )

                if activity_set:
                    activate_product = self.presta_put(request_url=MAIN_PRODUCTS_URL+product_id)

                    if activate_product.get("success"):
                        return True
        
        return False


    def stock_parser(self, 
                    quantity_to_transfer,
                    delete=True,
                    stock_list=None,
                    zero_quantity=False):

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
            
            self.stock_list = stock_list
            # Stocks parsing
            for i in stock_list:
                stock_page = requests.get(i, auth=(self.api_secret_key, ''))
                
                if stock_page.status_code == 200:
                    xml_content = ET.fromstring(stock_page.content)

                    # Get product id
                    id_product = xml_content[0].find('id_product').text

                    # Get total quantity from stock_availables
                    try:
                        self.quantity = int(xml_content[0].find('quantity').text)
                        if self.quantity >= 0 or mgmt_var > 0:
                            active_check = self.product_active_check(id_product)
                            
                            if active_check:
                                self.active_status = True

                    except Exception as e:
                        print("Product exists but not acvive yet!")

                    # Get product atribute
                    combination_link = xml_content[0].find('id_product_attribute')

                    # print(self.get_combination_link, " / ", combination_link.get('{http://www.w3.org/1999/xlink}href'))

                    # Verify product
                    # If global combination link and combination link from product card are eq.
                    # Than write global self.stock_url for future PUT request
                    # and decrease general quantity
                    if self.get_combination_link == combination_link.get('{http://www.w3.org/1999/xlink}href'):
                        self.stock_url = str(i)
                        print("Product with id " + str(id_product) + " will be delete! Total quantity: " + str(self.quantity))

                        if zero_quantity:
                            self.xml_response_create(0)
                            return 0

                        else:
                            total_q = int(self.quantity) + mgmt_var
                            self.xml_response_create(new_quantity=total_q, comb_check=True)

                            return total_q
                    else:
                        print("Product id: {}.".format(id_product), int(self.quantity), combination_link.text)
                else:
                    return stock_page.status_code
        else:
            return None


    def xml_response_create(self, new_quantity, comb_check=False):
        try:
            if comb_check and self.stock_list:
                self.check_default_comb(self.stock_list)

            get_stock_xml = requests.get(self.stock_url, auth=(self.api_secret_key, ''))
            
            xml_content = ET.fromstring(get_stock_xml.content)  # Create ET instanse and root tag
            general_tag = xml_content[0]  # Get prestashop tag
            tag = general_tag.find('quantity')

            tag.text = str(new_quantity)
            tag.set('update', 'yes')

            format_xml_tree = ElementTree(xml_content)
            format_xml_tree.write(os.path.join(self.base_dir, 'temp/log.xml'))

            self.restore_write_json(stock_url=self.stock_url, xml_data=get_stock_xml.text)

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
            return {'error': update_stocks.status_code}


    # The func try to find stock url from urlpattern: ['https://domain.com/api/stocks/?filter[reference]=KRHT..']
    # in warehouses
    # and return the stock link if product exists
    # or "Product does not exist!" str if not.
    # Return status_code another than 200 if something goes wrong.

    def stock_control(self, reference, warehouse, request_url=None):
        if request_url == None:
            request_url = "https://3gravity.pl/api/stocks/?filter[reference]=%[{}]%".format(reference)
        
        get_stock_content = requests.get(request_url, auth=(self.api_secret_key, ''))

        if get_stock_content.status_code == 200:
            response_data = []

            get_stock_url = self.get_ps_xml_tag(
                content=get_stock_content.content,
                tag="stock",
                find_all=True
            )

            if get_stock_url is None:
                return "Product does not exist!"


            if len(get_stock_url) >= 1:
                for i in get_stock_url:
                    response_data.append(i.get('{http://www.w3.org/1999/xlink}href'))
                    
                return self._wd(warehouse=warehouse, data=response_data)

        else:
            return get_stock_content.status_code


    def warehouse_quantity_mgmt(self,
                                warehouse,
                                reference,
                                quantity_to_transfer=None,
                                delete=True,
                                request_url=None,
                                zero_quantity=False):

        # Need for restore quantity if smth goes wrong
        self.save_quantity = None

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

            if zero_quantity:
                if int(get_physical_quantity.text) != 0:
                    self.get_product_attribute = general_product.find('id_product_attribute').text
                    self.get_product_id = general_product.find('id_product').text
                    self.save_quantity = get_physical_quantity.text

                    get_physical_quantity.text = '0'
                    get_usable_quantity.text = '0'
                
                else:
                    return -1

            else:
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
            
            self.restore_write_json(stock_url=request_url, xml_data=get_stocks_content.text)


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
        self.request_url = "https://3gravity.pl/api/combinations/?filter[reference]=%[{}]%".format(code)

        # Get link product on warehouse
        request_url_to = self.stock_control(warehouse=w_to, reference=code)

        stock_parser = self.stock_parser(
                                        quantity_to_transfer,
                                        delete=False)
        
        if stock_parser:
            add_bikes = self.presta_put()

            if request_url_to and add_bikes is not None:
                get_to_q = self.warehouse_quantity_mgmt(
                    warehouse=None,
                    quantity_to_transfer=quantity_to_transfer,
                    reference=None,
                    request_url=request_url_to,
                    delete=False
                    )
                

                if get_to_q:
                    update_warehouse = self.presta_put(request_url=get_to_q)
                


        if add_bikes is not None and update_warehouse is not None:
            self.w_to = w_to
            
            response_data = {
                'success': 'YES',
                'name': str(self.name),
                'quantity': str(self.total_quantity),
                'w_from': str(self.w_from),
                'w_to': str(self.w_to),
                'date': str(self.date),
                'restore_token': self.restore_id
            }

            return response_data

        else:
            return_error = {
                "error": "Unable to mooving products!",
                "name": str(self.name)
            }

            return return_error


    # Set up default combination if it has the lowest quantity or 0
    # Func takes comb_id for combination which will be setting up as default
    def set_default_combination(self, comb_id, value, check=True) -> bool:
        if comb_id is None:
            return False

        comb_url = requests.get(MAIN_COMBINATIONS_URL + comb_id, auth=(self.api_secret_key, ''))

        if comb_url.status_code != 200:
            return False
        
        # Check default field
        get_default_field = self.get_ps_xml_tag(
            content=comb_url.content,
            tag='default_on',
            find_all=False
        )


        if check:
            if get_default_field.text is None: return False
            if get_default_field.text: return True
        

        # If default_on field != 1? than combination is not default
        if not check:
            # Set up combination default_on at 1
            self.activity_reponse(
                comb_url.content,
                tag="default_on",
                value=value
            )

            # Update product
            put_combination = self.presta_put(request_url=MAIN_COMBINATIONS_URL+comb_id)

            if put_combination.get("success") is not None:
                return True

        return False
            

    # Using only in App classes for getting data for initializing
    def get_init_data(self, code):
        self.request_url = "https://3gravity.pl/api/combinations/?filter[reference]=%[{}]%".format(code)
        get_params = self.get_product_url()


        if isinstance(get_params, str):
            product_card = requests.get(get_params,auth=(self.api_secret_key, ''))

            if product_card.status_code != 200:
                return {"error": "Product url is invalid"}

            assoc_tag = self.get_ps_xml_tag(
            content=product_card.content,
            tag='associations',
            find_all=False
            )

            p_comb_id = assoc_tag.find('combinations')
            comb_dict = []

            for i in range(len(p_comb_id)):
                comb_dict.append(p_comb_id[i].find('id').text)
            
            if len(comb_dict) > 0:
                product_dict = {
                    get_params[-4:]: comb_dict
                }

                return product_dict

        else:
            return get_params


    # Save history to json
    def restore_write_json(self, stock_url, xml_data):
        xml_value = []

        try:
            with open(self.base_dir + "/AP/restore/session/restore.json", "r") as json_object:
                data = json.load(json_object)

        
        except Exception as e:
            data = {}
        

        if data.get(self.restore_id) is None:
            xml_value.append(xml_data)
            data.update({self.restore_id: {stock_url: xml_value}})
        
        else:
            existing_data = data.get(self.restore_id)
            value_check = existing_data.get(stock_url)
            
            if value_check is None:
                xml_value.append(xml_data)
                existing_data.update({stock_url: xml_value})
            
            else:
                value_check.append(xml_data)
                existing_data.update({stock_url: value_check})

            data.update({self.restore_id: existing_data})

            # Set privious dick history key as "yes"
            data_history_set = list(data.keys())

            if len(data_history_set) >= 2:
                update_by_key = data_history_set[-2]

                data.get(update_by_key).update({"history": "yes"})


        with open(self.base_dir + "/AP/restore/session/restore.json", "w") as json_object:
            json.dump(data, json_object, indent=4)

        return None


    # Delete all not filterable fields from xml string/document
    def not_filterable_delete(self, content):
        if content is None:
            return ""

        xml_content = ET.fromstring(content)
        general_tag = xml_content[0]

        # Not filterable delete
        not_filter_tags = []
            
        for not_filter in general_tag:
            if not_filter.get('notFilterable') == 'true':
                not_filter_tags.append(not_filter)

        for i in not_filter_tags:
            general_tag.remove(i)
            
        format_xml_tree = ET.tostring(xml_content, encoding="utf-8")

        return format_xml_tree


    # Restore last action. Restore token must be received from success "update" request
    # All of dicts in retore.json will be marked as "history" after succeed "restore" request
    def restore_last_action(self, restore_id):
        data = None

        with open(self.base_dir + "/AP/restore/session/restore.json", "r") as json_object:
            data = json.load(json_object)

        if data is None:
            return {"error": "Unable to cancle action!"}
        
        data_dict = data.get(restore_id)


        if data_dict.get("history") is None:
            for key, value in data_dict.items():
                for r in value:
                    resp_data = self.not_filterable_delete(r)
                    self.presta_put(response_data=resp_data, request_url=key)

            data_dict.update({"history": "yes"})

            with open(self.base_dir + "/AP/restore/session/restore.json", "w") as json_object:
                json.dump(data, json_object, indent=4)

        return {'OK': 'OK'}

        



