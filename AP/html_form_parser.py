"""
    Class HtmlFormParser forms the response body for POST-request and
    colelcting data from user's input-form in product add page.
"""

from bs4 import BeautifulSoup


class HtmlFormParser:
    request_data: dict
    action: str


    def __init__(self, html_object, stock_mvt_event=None):
        self.html_object = html_object
        self.stock_mvt_event = stock_mvt_event
    

    def form_finder(self):
        soup = BeautifulSoup(self.html_object, 'lxml')

        # Find form in response html
        root_form = soup.find('form', id="product_form")

        self.action = root_form.attrs["action"]

        return None if self.action is None else self.get_form_data(root_form)


    # Parse every input and add their data into "request_data" dict
    def get_form_data(self, form_values):
        if form_values is None:
            return {'error': 'Cannot parse form!'}

        # If we try to add product
        if self.stock_mvt_event == 'add':
            request_data = {
                'addstock': 1,
                'is_post': 1,
                'id_product': None,
                'id_product_attribute': None,
                'check': None,
                'quantity': None,
                'usable': 1,
                'id_warehouse': None,
                'price': 0,
                'id_currency': 1,
                'id_stock_mvt_reason': None,
            }

        # If we try to remove product
        if self.stock_mvt_event == 'remove':
            request_data = {
                'removestock': 1,
                'is_post': 1,
                'id_product': None,
                'id_product_attribute': None,
                'id_stock': None,
                'check': None,
                'quantity': None,
                'usable': 1,
                'id_stock_mvt_reason': None, # 2 - Spadek
            }
        
        if self.stock_mvt_event == 'transfer':
            request_data = {
                'transferstock': 1,
                'is_post': 1,
                'id_product': None,
                'id_product_attribute': None,
                'id_stock': None,
                'check': None,
                'quantity': None,
                'usable_from': 1,
                'usable_to': 1,
                'id_warehouse_to': None

            }

        for i in request_data.keys():
            get_input = form_values.find('input', {'name': i})
            
            if get_input is None:
                continue
            
            request_data.update({i: get_input.attrs.get('value')})
            self.request_data = request_data

        return request_data