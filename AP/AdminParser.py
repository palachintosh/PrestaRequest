import sys

sys.path.insert(0, '..')
# sys.path.append('/home/palachintosh/projects/mysite/mysite/bikes_monitoring/PrestaRequest/')


from .html_form_parser import HtmlFormParser
from mainp.PrestaRequest import PrestaRequest
from .AP_mixin import APMvmtMixin
from .auth_data import *
import requests
import logging
import os.path


class AdminParser(PrestaRequest, HtmlFormParser, APMvmtMixin):
    status = 0

    formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(message)s")
    base_sw_dir = os.path.dirname(os.path.abspath(__file__))
    file_handler = logging.FileHandler(base_sw_dir + "/logs/adn_parser.log")
    logger = logging.getLogger('adn_parser')
    logger.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.MAIN_ADN_LINK = MAIN_ADN_LINK
        self.adn_form_url = ADN_FORM_URL

        self.warehouses = ID_WAREHOUSES
    

    # Post request in stocks by admin !NOT API!
    def _w_post_request(self, request_data):
        # Make the post request on StockManagement
        main_url = MAIN_ADN_LINK + self.action

        add_post_req = self.rs.post(main_url, data=request_data)

        self.logger.info("W_post_request" + str(add_post_req.status_code))

        self.status = add_post_req.status_code

        if self.status == 200:
            return {'status': 'OK'}
        
        else:
            return {'status': 'FAIL'}


    # Authirization in PS admin
    def auth(self):
        self.rs = requests.Session()
        self.rs.get(MAIN_ADN_LINK)

        data = {
            'ajax': 1,
            'token': '',
            'controller': 'AdminLogin',
            'submitLogin': 1,
            'passwd': self.password,
            'email': self.login,
            'redirect': '127b7b8242e9acfe2138fa9d2d3dfa5d'
        }

        self.logger.info("Auth data: " + str(data))

        auth_request = self.rs.post(MAIN_ADN_LINK + "ajax-tab.php", data=data)
        self.status = auth_request.status_code


#============= Work with available stocks =============

    # New collector
    def post_data_collector(self, form_response, from_war_id, event):
        get_form = self.form_values(
                data=form_response,
                quantity=1,
                stock_mvmt_flag=1,
                form_war_id=from_war_id,
                stock_mvt_event=event
                )

        self.logger.debug("GET_FORM " + str(get_form))
        return get_form


    # Add stock for selected combination
    def adn_add_stock(self, id_product, comb_id):
        # Init vars inside class
        self.product_id = id_product
        self.comb_id = comb_id

        # Make attempt to get_form
        mvt_attempt = self.mvmt_product_mixin(mvmt_event='add')

        self.logger.info("ADN_STOCK_ADD: " + str(mvt_attempt))

        if mvt_attempt.status_code == 200:
            # from_war_id always eq. 4 (SHOP)
            pd = self.post_data_collector(
                form_response=mvt_attempt.text,
                from_war_id=4,
                event='add')

            self.logger.warning(str(pd))

            if not pd is None:
                # confirm_post = input("All data was colected! Do you wanna POST? Yes/any: ")
                # if confirm_post == 'Yes':
                
                add_post = self._w_post_request(pd)
                if add_post.get('status') == "OK":
                    return add_post

                else:
                    return {'error': 'FAIL'}
        
        return mvt_attempt.status_code

        
    # Remove one position from stocks
    def adn_remove_stock(self, id_stock, id_product, comb_id, id_warehouse):
        self.id_stock = id_stock
        self.product_id = id_product
        self.comb_id = comb_id

        mvt_attempt = self.mvmt_product_mixin(mvmt_event='remove')

        self.logger.info(str(mvt_attempt))

        if mvt_attempt.status_code == 200:
            pd = self.post_data_collector(
                form_response=mvt_attempt.text,
                from_war_id=id_warehouse,
                event='remove')

            self.logger.warning(str(pd))
            
            if not pd is None:
                print(pd)
                # confirm_post = input("All data was colected! Do you wanna POST? Yes/any: ")
                # if confirm_post == 'Yes':
                #     return self._w_post_request(pd)
                remove_post = self._w_post_request(pd)
                
                if remove_post.get('status') == "OK":
                    return remove_post

                else:
                    return {'error': 'FAIL'}

        return mvt_attempt.status_code

    # Transfer position between stocks
    def adn_transfer_stock(self, id_stock, id_product, comb_id, id_war_to):
        self.id_stock = id_stock
        self.product_id = id_product
        self.comb_id = comb_id
        self.id_war_to = id_war_to

        mvt_attempt = self.mvmt_product_mixin(mvmt_event='transfer')

        self.logger.info(str(mvt_attempt))

        if mvt_attempt.status_code == 200:
            pd = self.post_data_collector(
                form_response=mvt_attempt.text,
                from_war_id=id_war_to,
                event='transfer'
            )
            
            self.logger.warning(str(pd))

            if not pd is None:
                # Removing unusable values
                pd.update({'id_warehouse_to': id_war_to})
                pd.pop('id_stock_mvt_reason', None)
                pd.pop('id_warehouse', None)

                # confirm_post = input("All data was colected! Do you wanna POST? Yes/any: ")
                # if confirm_post == 'Yes':
                #     return self._w_post_request(pd)
                transfer_post = self._w_post_request(pd)
                
                if transfer_post.get('status') == "OK":
                    return transfer_post

                else:
                    return {'error': 'FAIL'}
        
        return mvt_attempt.status_code


#============= Ending work with available stocks =============


    # Forming post dict with HtmlFormParser
    def form_values(self,
                    data,
                    quantity,
                    stock_mvmt_flag,
                    form_war_id,
                    stock_mvt_event=None):

        HtmlFormParser.__init__(self, data, stock_mvt_event=stock_mvt_event)
        request_params = self.form_finder()

        if not request_params is None:
            request_params.update({
                'quantity': quantity,
                'id_stock_mvt_reason': stock_mvmt_flag,
                'id_warehouse': form_war_id,
            })

            return request_params

