# This is the main launcher of AdminParser lib.
# The file including general AdminParser classes and parsers for PrestaShop.
# AP_main provides access to other classes for parsing and is an adapter
# between palachintosh.com API and PrestaRequest lib.

# Every class in this file provides access to self functions.
# If I want to get all products_id - I need to call ProductsId class,
# for initializing stocks - just call the StockWorker etc. 

from sys import api_version, argv
from time import sleep
from .products_api import *
from .stock_worker import StocksWorker
from .auth_data import ID_WAREHOUSES, AUTH_DATA

import json
import logging

# Logger conf
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(message)s")
base_dir = os.path.dirname(os.path.abspath(__file__))
file_handler = logging.FileHandler(base_dir + "/logs/stock_worker.log")
logger = logging.getLogger('stock_worker_log')
logger.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


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
        

    def sw_main_cycle(self, product_id=None, comb_list=None, use_file=False):
        ap_response_status = {}

        if use_file:
            self.sw_file_object()
            if not self.file_object:
                return {"error": "File not found!"}
        
        else:
            self.file_object = {product_id: comb_list}


        terminal_size = os.get_terminal_size().columns
        array_len = len(self.file_object)
        counter = 1

    
        # Parsing file
        for product_id, comb_list in self.file_object.items():
            for comb_id in comb_list:

                attempt_resp = self.stock_checker(
                    comb_id=comb_id,
                    product_id=product_id)
                
                ap_response_status.update(attempt_resp)
                sleep(1)

                # Add loader for visualizanion process
                # ------------------------------------
                current_proc = 100 / (array_len / counter)

                if int(current_proc) >= 2 and int(current_proc) <= 100:
                    str_tag = int(current_proc / 2)
                    current_proc = "{:.2f}".format(current_proc)

                    if terminal_size > 91:
                        loading_str = "Loading: [_" + "#"*str_tag + "_"*(50-str_tag) + "_]" + f" {current_proc} / 100%"
                        
                    else:
                        loading_str = "Loading: [" f" {current_proc} / 100% ]"
                        print(loading_str, end='\r')

            counter += 1
            
        print('\n', 'Loading completed..')

        return ap_response_status


    # In manual mode function parsing try to init products form json file
    # Also, I can run this for ONE selected product calling this from custom
    # product_in and comb_id
    def stock_checker(self, comb_id, product_id):
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
                logger.error(init_stocks)
                
                ap_response_status.update({
                    "error": init_stocks
                })
                return ap_response_status
            
            log_str = f"Product {self.product_id} with comb. {comb_id} was added."
            logger.info(log_str)
            ap_response_status.update({"success": log_str})

        else:
            log_str = f"Product {self.product_id} with comb. {comb_id} already exists."
            logger.debug(log_str)
            ap_response_status.update({"success": log_str})


        return ap_response_status
