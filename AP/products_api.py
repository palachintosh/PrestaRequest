# This handler gets all products from products api
# and forming the list with all id_values

# import PrestaRequest module
import sys

# sys.path.insert(0, '..')
sys.path.append('/home/palachintosh/projects/mysite/mysite/bikes_monitoring/PrestaRequest/')

from datetime import datetime
from mainp.api_secret_key import api_secret_key
from mainp.PrestaRequest import PrestaRequest
from xml.etree import ElementTree as ET
from AP.auth_data import MAIN_API_URL
import requests
import json
import os


class ProductApi(PrestaRequest):
    def __init__(self):
        self.api_session = requests.Session()
        self.main_url = 'https://3gravity.pl/api/products/'
        self.product_add_info = {}
        self.verbose = False
        self.file_name = None


        # PrestaRequest initial
        super().__init__(api_secret_key)

    
    def get_all_products(self, request_url=None):
        if not request_url is None:
            request_url = self.main_url
        
        # get request to main products API
        get_all_products = self.api_session.get(
            self.main_url,
            auth=(self.api_secret_key, ''))
        
        if get_all_products.status_code == 200:
            id_list = self.xml_products_parser(get_all_products.content)

            if id_list.get('status') == 'OK':
                
                return self.get_all_active(id_list.get('id_values'))


    def get_ps_xml_tag(self, content, tag, find_all=True):
        xml_content = ET.fromstring(content)
        main_tag = xml_content[0]
        if find_all:    
           return main_tag.findall(tag)

        else:
            return main_tag.find(tag)


    # Parsing all products in store
    def xml_products_parser(self, data):
        id_values_array = []

        products = self.get_ps_xml_tag(
            content=data, 
            tag='product'
            )
        
        for product in products:
            id_values_array.append(product.get('id'))
        
        def sort_func(e):
            return int(e)

        id_values_array.sort(key=sort_func)
        
        resp_data = {
            'status': 'OK',
            'id_values': id_values_array
        }
        return resp_data 


    #Get ID and combinations ID
    def get_product_attribute(self, product_card):
        p_id = self.get_ps_xml_tag(
            content=product_card,
            tag='id',
            find_all=False)
        

        assoc_tag = self.get_ps_xml_tag(
            content=product_card,
            tag='associations',
            find_all=False
        )

        p_comb_id = assoc_tag.find('combinations')
        comb_dict = []

        for i in range(len(p_comb_id)):
            comb_dict.append(p_comb_id[i].find('id').text)
        
        if len(comb_dict) > 0:
            self.product_add_info.update({p_id.text: comb_dict})
            return 1

        return None


    def stock_info_check(self, product_card):
        get_value = self.get_ps_xml_tag(
            content=product_card,
            tag='advanced_stock_management',
            find_all=False
            )
        if get_value.text == '1':
            return True
        
        return False



    def get_all_active(self, id_values) -> dict:
        stock_id_arr = []
        array_len = len(id_values)
        counter = 0
        total_time = None
        expected_time = 0
        terminal_size = os.get_terminal_size().columns

        for id in id_values:
            # if counter == 500:
            #     break

            start_time = datetime.now()
            get_product_info = self.api_session.get(
                self.main_url + id,
                auth=(self.api_secret_key, ''))

            if get_product_info.status_code == 200:
                check_stamp = self.stock_info_check(get_product_info.content)

                if check_stamp:
                    prod_attr = self.get_product_attribute(get_product_info.content)
                    
                    if not prod_attr is None:
                        # stock_id_arr.append()
                        stock_id_arr.append(id)

                        if self.verbose:
                            print(id)

            total_time = datetime.now() - start_time

            counter += 1

            if counter == 1:
                expected_time = array_len*total_time.total_seconds()
                tmp_time = total_time
                print(expected_time)
                print(total_time.total_seconds())
            
            tmp_time += total_time
            
            current_proc = 100 / (expected_time / tmp_time.total_seconds())

            if int(current_proc) >= 2 and int(current_proc) <= 100:
                str_tag = int(current_proc / 2)
                current_proc = "{:.2f}".format(current_proc)

                if terminal_size > 91:
                    loading_str = "Loading: [_" + "#"*str_tag + "_"*(50-str_tag) + "_]" + " {} / 100%".format(current_proc)
                else:
                    loading_str = "Loading: [ {} / 100% ]".format(current_proc)

                print(loading_str, end='\r')

        print('\n', 'Loading completed..')

        if not self.product_add_info is None:
            self.json_dump_writer(self.product_add_info)

            return self.product_add_info


    # Write json dump with getted data
    def json_dump_writer(self, py_data) -> None:
        if self.file_name is None:
            self.file_name = 'system_products.json'

        with open("json_log/" + self.file_name, "w") as f:
            json.dump(py_data, f)

