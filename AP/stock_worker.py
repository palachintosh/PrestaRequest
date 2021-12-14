# The stock manager class
# Findes all of availables war stocks and
# edits them if need


from datetime import datetime

from django.views.generic import base
from requests.models import get_auth_from_url
from mainp.api_secret_key import api_secret_key
from .auth_data import MAIN_STOCK_URL, MAIN_COMBINATIONS_URL
from .products_api import ProductApi
from .AdminParser import AdminParser
import requests
import json
import logging
import os.path



class StocksWorker(AdminParser, ProductApi):

    impossible_to_add = {}
    operation_status = None
    stock_url = MAIN_STOCK_URL
    stock_xml_urls = []
    ref_array = None

    product_id = comb_id = stock_id = None


    formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(message)s")
    base_sw_dir = os.path.dirname(os.path.abspath(__file__))
    file_handler = logging.FileHandler(base_sw_dir + "/logs/SW.log")
    sw_logger = logging.getLogger('stock_worker_log.stock_logger')
    sw_logger.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    sw_logger.addHandler(file_handler)


    # Func checks if stock available in warehouse and return boolean value
    def stock_finder(self, comb_id=None) -> int:
        self.stock_xml_urls = []
        self.comb_id = comb_id

        get_stock_list = requests.get(
                self.stock_url + "?filter[id_product_attribute]={}".format(self.comb_id),
                auth=(api_secret_key, ''))
        
        stock_xml_data = self.get_ps_xml_tag(
            content=get_stock_list.content,
            tag='stock')
        
        # Wtite stocks in self var
        for i in stock_xml_data:
            self.stock_xml_urls.append(i.get('id'))
            
        
        # If returned value has 3 stocks -
        # just return True, cause thats ok for regular product.
        if len(self.stock_xml_urls) == 3:
            self.sw_logger.info("STOCKS FOR EXISTING PRODUCT: " + str(self.stock_xml_urls))
            return 3
        
        # Make returne value availables inside class
        if len(stock_xml_data) > 0:
            return len(self.stock_xml_urls)
        
        return 0


    # Check, does this stock available or not
    def stock_war_values_checker(self):
        if self.rs is None:
            self.auth()

            if self.status != 200:
                self.sw_logger.critical("Invalid auth data or sever doesn't respond! " + str(self.status))
                return "Invalid auth data or sever doesn't respond! {}".format(self.status)


        stocks = len(self.stock_xml_urls)

        if stocks >= 0:
            return self.stock_init_all()


    def stock_add_first(self):
        # First of all, we must add product on first stock in SHOP war.
        add_product = self.adn_add_stock(id_product=self.product_id, comb_id=self.comb_id)

        # Update stocks
        self.stock_finder(self.comb_id)

        self.sw_logger.info(str(add_product))

        if add_product.get('status') == 'OK' and self.stock_xml_urls:
            return True

        return False


    def imposible_var_log(self):
        import os.path

        base_imposible_dir = os.path.dirname(os.path.abspath(__file__))

        if self.impossible_to_add.get(self.product_id) is None:
            self.impossible_to_add.update({
                    self.product_id: [self.comb_id]
                })

        else:
            get_comb = self.impossible_to_add.get(self.product_id)
            get_comb.append(self.comb_id)

            self.impossible_to_add.update({
                self.product_id: get_comb
            })
        
        with open(base_imposible_dir + "/logs/impossible_.json", "w") as f:
            json.dump(self.impossible_to_add, f)


    # If noone is available - init them using AdminParser finctional
    def stock_init_all(self, first_init=False):
        if not first_init:
            first_step = self.stock_add_first()

            if not first_step:
                self.imposible_var_log()

                return False

        if len(self.stock_xml_urls) > 0:
            transfer = True

            for war_id in range(5, 7):
                if transfer:
                    stock_for_next_transfer = self.stock_shop_finder(str(war_id-1))
                    
                    transfer_stock = self.adn_transfer_stock(
                        id_stock=stock_for_next_transfer,
                        id_product=self.product_id,
                        comb_id=self.comb_id,
                        id_war_to=war_id,
                        )
                    
                    self.stock_finder(self.comb_id)

                    if transfer_stock.get('status') != 'OK':
                        self.sw_logger.error("ERROR WHILE TRANSFER: " + str(transfer_stock))
                        transfer = False
                        self.imposible_var_log()
                        break

            if transfer:
                stock_for_remove = self.stock_shop_finder('6')

                if not stock_for_remove is None:
                    remove_stock = self.adn_remove_stock(
                        id_stock=stock_for_remove,
                        id_product=self.product_id,
                        comb_id=self.comb_id,
                        id_warehouse=6
                        )
                    
                    if remove_stock.get('status') == 'OK':
                        return True
        
                    self.sw_logger.error("ERROR WHILE REMOVE: " + str(transfer_stock))

        self.imposible_var_log()
        return None


    def stock_shop_finder(self, war_id):
        if not self.stock_xml_urls is None and len(self.stock_xml_urls) > 0:
            for stock in self.stock_xml_urls:
                stock_get_warehouse = requests.get(
                    self.stock_url + stock,
                    auth=(api_secret_key, ''))
                
                if stock_get_warehouse.status_code == 200:
                    # Get warehouse id from id_warehouse tag
                    stock_warehouse_id = self.get_ps_xml_tag(
                        content=stock_get_warehouse.content,
                        tag='id_warehouse', find_all=False)
                
                    if stock_warehouse_id.text == war_id:
                        return stock
        
        return None


    def stock_ref_checker(self, comb_id) -> bool:
        get_ref_page = requests.get(
                    MAIN_COMBINATIONS_URL + str(self.comb_id),
                    auth=(api_secret_key, ''))


        if get_ref_page.status_code == 200:
            reference_str = self.get_ps_xml_tag(
                content=get_ref_page.content,
                tag="reference",
                find_all=False
            )

            if reference_str.text:
                self.ref_array = reference_str.text.split(' ')

                if len(self.ref_array) == 1:
                    return True
                
                else:
                    return False
        
        return False
            


