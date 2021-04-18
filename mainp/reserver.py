from .PrestaRequest import PrestaRequest
from .db.db_writer import ReserveBikes
import datetime

class Reserve(PrestaRequest):

    url_to_delete = None


    def delete_or_add(self, comb_id, phone_number, delete=True):
        # if quantity == 1, than add product in united stocks
        quantity = 0
        print("IN DELTETE BLOCK!")
        rb = ReserveBikes(name=None)
        r_check = rb.get_reservation(comb_id, phone_number)
        
        if r_check != None:
            quantity = int(r_check[-2])

        if self.url_to_delete == None:
            return {'error': 'Url required!'}
        

        self.get_combination_link = self.url_to_delete

        if comb_id != None:
            delete_with_combination = self.get_product_url(request_url=self.url_to_delete)
            comb_delete = self.get_product_stocks_url(request_url=delete_with_combination)

            if delete_with_combination != None and comb_delete != None:
            
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

                    if delete_data != None and stock_url != None:
                        pp = self.presta_put(request_url=stock_url)

                        if pp != None:
                            return {"success": "Success.Quantity after transaction >>>: {}".format(delete_data, stock_url)}
                        pass

                except Exception as e:
                    return str(e)


                print("Quantity after delete >>>: ", delete_data, print(stock_url))
            else:
                return None


    def add_new(self, comb_id, qty=1, phone_number='', reference=''):
        rb = ReserveBikes()
        rb_write = rb.create_db()
        print("Status_code", rb_write)

        if rb_write == 0:
            print('ADD BLOCK')
            dt = datetime.datetime.strftime(datetime.datetime.today(), '%Y%m%d'),
            print(type(dt), dt)

            insert_data = [(
                        dt[0],
                        str(phone_number),
                        str(comb_id),
                        reference,
                        1,
                        qty
                    )]

            mr = rb.make_reservation(insert_data)
            if mr == 1:
                update_psdb = self.delete_or_add(comb_id=comb_id, phone_number=phone_number)
                return update_psdb

        return None


    def reserve_check(self, comb_id, phone_number):
        print("==============================", comb_id)

        rb = ReserveBikes(name=None)
        r_check = rb.get_reservation(comb_id, phone_number)

        print("R_CHECK: ", r_check)
        
        if r_check != None:
            if r_check[2] == phone_number and r_check[-1] != 0:
                return {'Warning': "Reservation for this client is active now!"}

            if r_check[2] == phone_number and r_check[-1] == 0:
                return {"Warning": "Rezerwation with phone '{}' is NOT active now!".format(str(phone_number))}

            else:
            # return "Unable to add reservation for comb {}".format(comb_id)
                return None

        else:
            add_reserve = self.add_new(
                comb_id=comb_id,
                phone_number=phone_number,
                reference=''
                )
            
            if add_reserve == 1:
                # return self.delete_or_add(comb_id=comb_id, phone_number=phone_number)
                pass


            return add_reserve



# The Cancel reservation button.
# Disable each reservtion in db, with active_stamp=1
# If reservation does not exist - do nothing.

    def deactivate(self, comb_id, phone_number):

        rb = ReserveBikes(name=None)
        r_check = rb.get_reservation(comb_id, phone_number)

        if r_check != None:
            if r_check[2] == phone_number and r_check[-1] != 0:
                deactivate = rb.deactivate_reservation(comb_id=comb_id, phone_number=phone_number, active_stamp=0)

                if deactivate == 1:
                    delete_after_reserve = self.delete_or_add(
                        comb_id=comb_id,
                        phone_number=phone_number,
                        delete=False,
                    )

                    if delete_after_reserve:
                        return {
                            "Warning": "Rezerwation with phone '{}' is NOT active anymore!".format(str(phone_number)),
                            "Success": delete_after_reserve,
                        }


                    return delete_after_reserve
        return None


    def only_deactivate(self, comb_id, phone_number):
        rb = ReserveBikes(name=None)
        r_check = rb.get_reservation(comb_id, phone_number)
        print("==================Only deactivate ", r_check)

        if r_check != None:
            if r_check[2] == phone_number and r_check[-1] != 0:
                deactivate = rb.deactivate_reservation(
                    comb_id=comb_id,
                    phone_number=phone_number
                    )
                
                print("-----------", deactivate)
                
                if deactivate == 1:
                    return {'Success': 'Rezerwzcja nie aktywna!'}
        else:
            return {'Warning': 'Brak rezerwacji dla tego numeru!'}
