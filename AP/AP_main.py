# This is the main launcher of AdminParser lib.
# The file including general AdminParser classes and parsers for PrestaShop.
# AP_main provides access to other classes for parsing and is an adapter
# between palachintosh.com API and PrestaRequest lib.

# Every class in this file provides access to self functions.
# If I want to get all products_id - I need to call ProductsId class,
# for initializing stocks - just call the StockWorker etc. 

from sys import argv
from time import sleep
from .products_api import *
from .stock_worker import StocksWorker
from .auth_data import ID_WAREHOUSES, AUTH_DATA

import json
import logging
import os.path



# Class will collecting products for tests
class APProductsCollector(ProductApi):
    def collect_all(self):
        if "-v" in argv:
            self.verbose=True
        
        self.file_name = "p_data.json"
        
        # Get all products
        get_all_products = self.get_all_products()

        try:
            with open("json_log/" + self.file_name) as f:
                print("All data was collected!")

        except FileNotFoundError as e:
            return e
        
        return get_all_products




# This class managing stocks. Add, delete and transfer
class APStockWorker(StocksWorker):
    # Try to desrialize json file from "json_log"
    # Logger conf
    formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(message)s")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_handler = logging.FileHandler(base_dir + "/logs/stock_worker.log")
    logger = logging.getLogger('stock_worker_log')
    logger.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    def __init__(self, login, password):
        super().__init__(login, password)
        self.file_object = None
    

    def sw_file_object(self):
        try:
            # with open("json_log/p_data.json") as f:
            with open("json_log/test_j.json") as f:
                self.file_object = json.loads(f.read())

        except FileNotFoundError:
            pass

        else:
            return None
        

    def sw_main_cycle(self, product_id=None, comb_list=None, use_file=False, force=False):
        ap_response_status = {}

        if use_file:
            self.sw_file_object()
            if not self.file_object:
                ap_response_status.update({"error": "File not found!"})
                return ap_response_status
        else:
            self.file_object = {product_id: comb_list}
        
        if self.file_object is None:
            ap_response_status.update({'error': 'Unable to parse selected product!'})
            return ap_response_status
        

        self.logger.warning("CYCLE: " + str(self.file_object) + str(product_id) + str(comb_list))
    
        # Parsing file or dict
        for product_id, comb_list in self.file_object.items():
            for comb_id in comb_list:
                attempt_resp = self.stock_checker(
                    comb_id=comb_id,
                    product_id=product_id,
                    force=force)
                
                ap_response_status.update(attempt_resp)
                sleep(1)

        return ap_response_status


    # In manual mode function parsing try to init products form json file
    # Also, I can run this for ONE selected product calling this from custom
    # product_in and comb_id
    def stock_checker(self, comb_id, product_id, force=False):
        ap_response_status = {}
        
        # Init product id inside class
        self.product_id = str(product_id)

        # Launch main stock_finder function with comb_id param
        stock_checker = self.stock_finder(comb_id=str(comb_id))
        

        # If stock count == 3 return dict with success
        # Else try to init stocks on warehouses
        if stock_checker != 3:
            init_stocks = self.stock_war_values_checker()
            
            if isinstance(init_stocks, str):
                self.logger.error(init_stocks)
                
                ap_response_status.update({
                    "error": init_stocks
                })

                return ap_response_status
            
            log_str = "Product {} with comb. {} was added.".format(self.product_id, comb_id)
            self.logger.info(log_str)
            ap_response_status.update({"success": log_str})


        else:
            if stock_checker == 3:
                # Need to check the quantity of references in combination.
                # If this > 1 - init stocks in "force" mode.
                # references_array = self.stock_ref_checker(comb_id=self.comb_id)
                # if forse

                if not force:
                    log_str = "Product {} with comb. {} already exists.".format(self.product_id, comb_id)
                    self.logger.debug(log_str)
                    ap_response_status.update({"success": log_str})

                else:
                    init_stocks = self.stock_war_values_checker()

                    if isinstance(init_stocks, str):
                        self.logger.error(init_stocks)
                        
                        ap_response_status.update({
                            "error": init_stocks
                        })
                        
                        return ap_response_status

                    log_str = "Product {} with comb. {} exists, but was updated in force mode.".format(self.product_id, comb_id)
                    self.logger.debug(log_str)
                    ap_response_status.update({"success": log_str})


        return ap_response_status
