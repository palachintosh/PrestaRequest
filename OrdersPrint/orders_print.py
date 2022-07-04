import sys
sys.path.insert(0, '..')
# sys.path.append('/home/palachintosh/projects/mysite/mysite/bikes_monitoring/PrestaRequest/')


from mainp.PrestaRequest import PrestaRequest
from mainp.var import MAIN_API_URL
#from mainp.api_secret_key import api_secret_key
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ElementTree
from fpdf import FPDF
from datetime import date, timedelta, datetime
import os

import logging

import requests


class OrdersPrint(PrestaRequest):
    orders_list = {}
    not_acceptable_order_states = ['4', '5', '6', '7', '8', '9', '13']
    total_bikes_to_pickup = 0
    ev_orders_products = []


    formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(message)s")
    base_op_dir = os.path.dirname(os.path.abspath(__file__))
    file_handler = logging.FileHandler(base_op_dir + "/orders_print.log")
    op_logger = logging.getLogger('stock_worker_log.stock_logger')
    op_logger.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    op_logger.addHandler(file_handler)


    def get_orders_by_date(self, orders_url):
        get_orders = requests.get(orders_url, auth=(self.api_secret_key, ''))

        if get_orders.status_code == 200:
            orders_collected_list = self.parse_orders(get_orders.content)
            
            if orders_collected_list and not isinstance(orders_collected_list, str):
                return orders_collected_list
            
            if isinstance(orders_collected_list, str):
                return orders_collected_list

        return None


    def get_orders_by_id(self, orders_url) -> dict:
        self.op_logger.info("GET ORDERS BY ID: " + str(orders_url))
        get_orders = requests.get(orders_url, auth=(self.api_secret_key, ''))

        self.op_logger.info("COLLECT_BY LIMIT. STATUS: " + str(get_orders.status_code))
        self.op_logger.info("COLLECT_BY LIMIT: " + str(get_orders.text))

        if get_orders.status_code == 200:
            orders_collected_list = self.parse_orders(get_orders.content, date_prefix=True)
            self.op_logger.info("COLLECTED LIST _1: " + str(orders_collected_list))
        
            if orders_collected_list and not isinstance(orders_collected_list, str):
                self.op_logger.info("COLECTED_ LIST: " + str(orders_collected_list))
                return orders_collected_list
            
            if isinstance(orders_collected_list, str):
                return orders_collected_list

        return None


    def collect_by_limit_url(self, limit_id_start, limit_id_end):
        try:
            int(limit_id_start)
            int(limit_id_end)
        except:
            self.op_logger.info("COLLECT_BY LIMIT IN EXCEPT: " + str(limit_id_start) + str(limit_id_end))
            return None
        
        orders_url = MAIN_API_URL + 'orders/?filter[id]=[{},{}]'.format(limit_id_start, limit_id_end)
        daily_orders = self.get_orders_by_id(orders_url)
        
        if daily_orders is not None:
            self.orders_list = daily_orders

            return self.orders_list

        self.op_logger.info("COLLECT_BY LIMIT: " + str(orders_url))
        self.op_logger.info("COLLECT_BY LIMIT: " + str(daily_orders))
        self.op_logger.info("COLLECT_BY LIMIT: " + str(self.orders_list))

        return None


    def collect_orders_by_date(self, days_ago=0):
        if days_ago == 0:
            orders_limit_date = date.today()
            orders_url = MAIN_API_URL + 'orders/?filter[date_add]=%[{}]%&date=1'.format(orders_limit_date)            
            
            daily_orders = self.get_orders_by_date(orders_url)

            if daily_orders is not None:
                self.orders_list.update({orders_limit_date.strftime('%Y-%m-%d'): daily_orders})
                
                return self.orders_list

        
        if days_ago > 0:
            for day in range(days_ago+1):
                limit = date.today() - timedelta(days=day)
                orders_url = MAIN_API_URL + "orders/?filter[date_add]=%[{}]%&date=1".format(limit)
            
                daily_orders_list = self.get_orders_by_date(orders_url)

                if daily_orders_list is not None:
                    self.orders_list.update({limit.strftime('%Y-%m-%d'): daily_orders_list})

            return self.orders_list
        
        return None


    def visible_orders(self, content):
        xml_content = ET.fromstring(content)
        main_tag = xml_content[0]

        if main_tag:
            return main_tag.findall('order')

        return None


    def product_name_validator(self, product_name):
        if product_name is None:
            return None
        
        str_arr = product_name.split(' ')
        if str_arr[0] != 'Kross' and str_arr[0] != 'Le':
            return None

        try:
            if str_arr[0] == 'Kross':
                str_arr.remove('Kross')
            if str_arr[0] == 'Le':
                str_arr.remove('Le')
                str_arr.remove('Grand')

            size_idex = str_arr.index('Rozmiar')
            str_arr.remove('Rozmiar')
            str_arr.remove(':')
            str_arr.remove(':')

        except:
            validate_str = ' '.join(str_arr)

        validate_str = ' '.join(str_arr[:size_idex+2:]).rstrip('-').replace(' / ', '/')

        return validate_str

    
    def order_phone_number(self, order_address_id):
        if order_address_id is None:
            return 'N/A'
        
        address_url = MAIN_API_URL + 'addresses/' + order_address_id
        get_address_page = requests.get(address_url, auth=(self.api_secret_key, ''))

        if get_address_page.status_code == 200:
            xml_content = ET.fromstring(get_address_page.content)
            phone_mobile = xml_content[0].find('phone_mobile').text
            phone = xml_content[0].find('phone').text

            if phone_mobile is not None:
                return phone_mobile
            
            if phone is not None:
                return phone
            
        
        return 'N/A'


    def order_status_check(self, order_state):
        accept = ['2', '3', '11', '12']

        if order_state in accept:
            return ''
        
        return 'N/Z'


    def pickup_check(self, pickup_rate):
        if pickup_rate == '33':
            return 'Od/Sklep'
        
        return ''


    def get_order_detail(self, order_id):
        info_url = MAIN_API_URL + 'orders/{}'.format(order_id)
        order_info = requests.get(info_url, auth=(self.api_secret_key, ''))

        if order_info.status_code != 200:
            return None
        
        xml_content = ET.fromstring(order_info.content)
        order_row = xml_content[0].find('associations').find('order_rows').findall('order_row')
        order_address_id = xml_content[0][1].text
        order_state_id = xml_content[0].find('current_state').text
        final_state = self.order_status_check(order_state_id)
        pickup_in_shop = self.pickup_check(xml_content[0].find('id_carrier').text)
        date_add = datetime.strptime(
            xml_content[0].find('date_add').text, '%Y-%m-%d %H:%M:%S').date().strftime('%Y-%m-%d')


        info_set = {
            'xml_content': xml_content,
            'order_row': order_row,
            'order_address_id': order_address_id,
            'order_state_id': order_state_id,
            'final_state': final_state,
            'pickup_in_shop': pickup_in_shop,
            'date_add': date_add
            }

        return info_set


    def make_printable_str(self, order_id):
        order_list_line = {}
        order_info = self.get_order_detail(order_id)

        if order_info is None:
            return None
        
        if order_info['order_state_id'] in self.not_acceptable_order_states:
            return None

        for row in order_info['order_row']:
            product_name = self.product_name_validator(row.find('product_name').text)
            quantity = row.find('product_quantity').text

            if product_name is not None:
                p_num = self.order_phone_number(order_info['order_address_id'])
                final_str = str(order_id) + '  | ' + product_name
                
                if quantity != '1':
                    final_str = final_str + '({})'.format(quantity) + ' | '
                
                final_str = final_str + str(p_num)

                if order_info['pickup_in_shop']:
                    final_str = final_str + ' | ' + order_info['pickup_in_shop']
                
                if order_info['final_state']:
                    final_str = final_str + ' | ' + order_info['final_state']
                
                self.ev_orders_products.append(final_str)

                if order_list_line.get(order_info['date_add']) is None:
                    order_list_line.update({order_info['date_add']: {p_num: self.ev_orders_products}})
                # else:
                #     order_list_line.get(order_info['date_add']).update({'x2': self.ev_orders_products})

        self.ev_orders_products = []

        return order_list_line
    

    def make_with_prefix(self, start_str, daily_orders, date_prefix=False):
        start_keys = list(start_str.keys())[0]

        if date_prefix:
            if daily_orders:
                get_date = daily_orders.get(start_keys)

                if get_date is None:
                    return start_str

                else:
                    daily_orders.get(start_keys).update(start_str.get(start_keys))
                    return daily_orders
                    
            return start_str
        
        else:
            return start_str.get(start_keys)



    def parse_orders(self, content, date_prefix=False):
        daily_orders = {}

        orders_tree  = self.visible_orders(content)
        if orders_tree is None:
            return "No orders today :)"

        for order in orders_tree:
            start_str = self.make_printable_str(order.attrib['id'])
            
            if start_str and start_str is not None:
                # daily_orders.append(start_str)
                if date_prefix:
                    daily_orders.update(
                        self.make_with_prefix(start_str, daily_orders, date_prefix))
                    # daily_orders = self.make_with_prefix(start_str, daily_orders, date_prefix)
                else:
                    daily_orders.update(
                        self.make_with_prefix(start_str, daily_orders)
                    )

        self.op_logger.info("PARSE ORDERS: " + str(daily_orders))
        return daily_orders


    def _orders_counter(self, orders_dict):
        counter = 0

        for key, line in orders_dict.items():
            if isinstance(line, dict):
                for phone, order in line.items():
                    for final_line in order:
                        counter += 1
        
        return counter

    def to_pdf(self, orders_dict, total=0, date=date.today().strftime('%Y/%m/%d'), card_path=None):
        file_name = None

        if orders_dict is None:
            orders_dict = self.orders_list

        if total == 0:
            total = self._orders_counter(orders_dict)

        if total == 0:
            buses = 0
        else:
            buses = int(total/13) + 1
        
        if card_path is None:
            file_name = 'orders-{}.pdf'.format(datetime.today().date())
            card_path = os.path.join(self.base_dir, 'print/' + file_name)
        
    
        class PDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 12)
                self.total = 0
                # Title
                self.cell(0, 10, 'Total: {}'.format(total) + '       ' + 'Kursy: {}'.format(buses) + '       ' + 'Data: ' + date, 0, 0, 'C')
                # Line break
                self.ln(20)

        pdf = PDF('P', 'pt', 'A4')
        pdf.add_page()
        pdf.add_font(
            'DejaVu',
            '', 
            os.path.join(self.base_dir, 'OrdersPrint/DejaVuSans.ttf'),
            uni=True)
        
        pdf.set_font('DejaVu', '', 10)

        for key, line in orders_dict.items():
            pdf.cell(0, 20, key, 0, 1)

            if isinstance(line, dict):
                for phone, order in line.items():
                    # print(phone, o_str)
                    for final_line in order:
                        pdf.cell(0, 20, final_line, 0, 1)
                
            else:
                pdf.cell(0, 20, line, 0, 1)
        
        # pdf.output('orders.pdf', 'F')
        pdf.output(card_path, 'F')

        return file_name


# if __name__ == "__main__":
#     ord = OrdersPrint(api_secret_key=api_secret_key)
#     # order_str = ord.collect_orders_by_date(days_ago=1)
#     # order_str = ord.collect_by_limit_url('3469', '3460')
#     order_str = ord.collect_by_limit_url('3420', '3482')

#     # print(order_str)
#     for key, value in order_str.items():
#         print(key)

#         if isinstance(value, dict):
#             for phone, o_str in value.items():
#                 print(phone, o_str)
            
#         else:
#             print(value)


#     if order_str:
#         ord.to_pdf(order_str, ord.total_bikes_to_pickup)

