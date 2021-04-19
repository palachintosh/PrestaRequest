import requests
from .PrestaRequest import PrestaRequest

from xml.etree import ElementTree as ET

class GetWarehousesValues(PrestaRequest):

    name_warehouses = {
            "4": 'shop',
            "5": 'x',
            "6": 'y'
        }

    def get_warehouses_links(self, request_url):
        if request_url != None:
            request_data = []
            get_stocks_page = requests.get(request_url, auth=(self.api_secret_key, ''))

            if get_stocks_page.status_code == 200:
                xml_content = ET.fromstring(get_stocks_page.content)  # Create ET instanse and root tag
                general_tag = xml_content[0]  # Get prestashop tag
                tag = general_tag.findall('stock')

                for i in tag:
                    tag_inner_link = i.get('{http://www.w3.org/1999/xlink}href')
                    request_data.append(tag_inner_link)

                return request_data
            
            else:
                return None
    
    def get_warehouses_values(self, request_data):
        warehouse = None
        combination = None
        quantity = 0

        response = {}

        for link in request_data:
            get_comb_data = requests.get(link, auth=(self.api_secret_key, ''))
            
            if get_comb_data.status_code == 200:
                xml_content = ET.fromstring(get_comb_data.content)
                general_tag = xml_content[0]

                warehouse =  self.name_warehouses.get(general_tag.find('id_warehouse').text)

                combination = general_tag.find('id_product_attribute').text
                quantity = general_tag.find('real_quantity').text

                response.update({warehouse: {
                    'combination': combination,
                    'quantity': quantity
                }})

        
            else:
                return None

        return response