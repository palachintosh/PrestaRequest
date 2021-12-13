# Mixins for add, remove and transfer product event

import requests

# from bikes_monitoring.PrestaRequest.AdminParser.auth_data import ID_WAREHOUSES


class APMvmtMixin:
    # From AdminParser __init__:
    adn_form_url = None
    rs= None
    
    # Other vars
    product_id = None
    comb_id = None
    id_stock = None


    def mvmt_product_mixin(self, mvmt_event=None) -> requests.Response:
        if mvmt_event == 'add':
            stock_url = (
                self.adn_form_url +
                "id_product={}&" # product id on stock availables
                "detailsproduct&" # static param
                "id_product_attribute={}&" # combination id
                "addstock&" # static param
                ).format(self.product_id, self.comb_id) # static param

        if mvmt_event == 'remove':
            stock_url = (
                self.adn_form_url +
                "id_stock={}&"
                "removestock&" # static param
                ).format(self.id_stock) # static param

        if mvmt_event == 'transfer':
            stock_url = (
                self.adn_form_url +
                "id_stock={}&"
                "transferstock&").format(self.id_stock)

        stock_url += "token=9eef0ce44086ae5255fa591518be9c60"
        stock_req = self.rs.get(stock_url)


        if stock_req.status_code == 200:
            return stock_req

        return None
