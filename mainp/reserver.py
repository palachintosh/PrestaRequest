from .PrestaRequest import PrestaRequest
from .db.db_writer import ReserveBikes
import datetime
# from bikes_monitoring.tasks import auto_delete_reserve

# 8507

class Reserve(PrestaRequest):
    url_to_delete = None
    db_data = None
    r_check = None


    def delete_or_add(self, delete=True):
        # if quantity == 1, than add product in united stocks
        quantity = 0
        rb = ReserveBikes(name=None)
        r_check = rb.get_reservation(
            comb_id=self.db_data["comb_id"],
            phone_number=self.db_data["phone_number"]
        )
        
        if r_check is not None:
            quantity = 1

        if self.url_to_delete is None:
            return {'error': 'Url required!'}
        

        self.get_combination_link = self.url_to_delete

        if self.db_data["comb_id"] is not None:
            delete_with_combination = self.get_product_url(request_url=self.url_to_delete)
            comb_delete = self.get_product_stocks_url(request_url=delete_with_combination)

            if delete_with_combination is not None and comb_delete is not None:
                try:
                    if delete:
                        delete_data = self.stock_parser(
                        quantity_to_transfer=quantity,
                        stock_list= comb_delete.get('stock_data')
                    )

                    else:
                        delete_data = self.stock_parser(
                            quantity_to_transfer=quantity,
                            stock_list= comb_delete.get('stock_data'),
                            delete=False
                        )

                    stock_url = self.stock_url
                    print(stock_url)
                    
                    # This construction will not delete last bike form stocks
                    # if delete_data and stock_url:
                    if isinstance(delete_data, int) and stock_url:
                        pp = self.presta_put(request_url=stock_url)

                        if pp is not None:
                            return {"success": "Quantity after transaction >>>: {}".format(delete_data, stock_url)}


                except Exception as e:
                    return str(e)

            else:
                if delete:
                    return {'Warning': 'Rezerwacja jest aktywna teraz, ale wybranego produktu nie ma na stanach!'}

                else:
                    return {'Warning': 'Rezerwacja zostala zamknieta, ale produkt nie wrócił na stany!'}


    def add_new(self):
        rb = ReserveBikes()
        dt = str(datetime.datetime.now())

        insert_data = [(
                        dt,
                        self.db_data.get('phone_number'),
                        '',
                        self.db_data.get('comb_id'),
                        self.db_data.get('reference'),
                        1, # quantity
                        self.db_data.get('permanent'), # "Premanent" new field
                        1,
                    )]

        mr = rb.make_reservation(insert_data)
        if mr == 1:
            update_psdb = self.delete_or_add()

            return update_psdb

        return None


    def reserve_check(self):
        # db_data - is phone_number, comb_id, username, off_time (in hours) and active stamp
        phone_number = self.db_data["phone_number"]

        rb = ReserveBikes()

        r_check = rb.get_reservation(
            comb_id=self.db_data["comb_id"],
            phone_number=phone_number)

        self.r_check = r_check

        if r_check is not None:
            if r_check[2] == phone_number and r_check[-1] == 1:
                return {'Warning': "Rezerwacja dla wybranego klienta teraz aktywna!"}
                # # return {'alert'}
                # # return 1
                # return {'success': 1}

            if r_check[2] == phone_number and r_check[-1] == 0:
                return {"Warning": "Rezerwacja '{}' istnieje ale nie aktywna!".format(phone_number)}

            # return None

        # else:
            # add_reserve = self.add_new()
            
            # if add_reserve == 1:
            #     # return self.delete_or_add(comb_id=comb_id, phone_number=phone_number)
            #     pass


            # return add_reserve
        return None



# The Cancel reservation button.
# Disable each reservtion in db, with active_stamp=1 and selected phone_number
# If reservation does not exist - do nothing.

    def deactivate(self):

        rb = ReserveBikes(name=None)
        r_check = rb.get_reservation(
            comb_id=self.db_data["comb_id"],
            phone_number=self.db_data["phone_number"])

        if r_check is not None:
            if r_check[2] == self.db_data["phone_number"] and r_check[-1] != 0:
                deactivate = rb.deactivate_reservation(
                    comb_id=self.db_data["comb_id"],
                    phone_number=self.db_data["phone_number"],
                    active_stamp=0)

                if deactivate == 1:
                    delete_after_reserve = self.delete_or_add(delete=False)

                    if delete_after_reserve:
                        return {
                            "Warning": "Rezerwacja z numerem '{}' nie aktywna!".format(self.db_data["phone_number"]),
                            "Success": delete_after_reserve,
                        }


                    return delete_after_reserve
        return None


    def only_deactivate(self):
        rb = ReserveBikes()
        r_check = rb.get_reservation(
            comb_id=self.db_data["comb_id"],
            phone_number=self.db_data["phone_number"]
        )

        self.r_check = r_check

        if r_check is not None:
            if r_check[2] == self.db_data["phone_number"] and r_check[-1] != 0:
                deactivate = rb.deactivate_reservation(
                    comb_id=self.db_data["comb_id"],
                    phone_number=self.db_data["phone_number"]
                    )
                
                if deactivate == 1:
                    return {'Success': 'Rezerwacja nie aktywna!'}
        else:
            return {'Warning': 'Brak rezerwacji z tym numerem!'}


    def get_active_reservation(self, comb_id):
        rb = ReserveBikes()
        get_active = rb.get_res_dict(
            comb_id=comb_id)
        
        if get_active:
            return get_active
        
        return None
    

    def add_task_id(self, task_id, phone_number, comb_id) -> bool:
        rb = ReserveBikes()
        r_check = rb.get_reservation(
            comb_id=comb_id,
            phone_number=phone_number)
        
        if r_check is not None:
            set_task_id = rb.add_task_id(task_id, r_check[0])

            if set_task_id == 1:
                return True
        
        return False

