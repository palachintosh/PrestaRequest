import os
import os.path
import sqlite3
from sqlite3.dbapi2 import connect

class ReserveBikes:
    def __init__(self, name=None):

        self.name = name
        
        if self.name == None:
            self.name = 'reserverd_bikes.db'

        self.base_path = os.path.dirname(os.path.abspath(__file__)) + '/' + self.name
        self.create_db()


    def _db_check(self):
        try:
            conn = sqlite3.connect('file:{}?mode=rw'.format(self.base_path), uri=True)
            print("Reading database..\n", "Done")
            conn.close()
            return 1

        except Exception as e:
            print("Error: unable to open database. File not exist!")
            return str(e)
        

    def create_db(self):

        if self._db_check() != 1:
            try:
                conn = sqlite3.connect(self.base_path)
                cursor = conn.cursor()
                cursor.execute("""CREATE TABLE IF NOT EXISTS reserve
                (id INTEGER PRIMARY KEY,
                created_at timestamp,
                phone_number text,
                comb_id text,
                reference text,
                qty INTEGER,
                active_stamp INTEGER)""")
                conn.commit()

                conn.close()
                print("Database has been created successfully")

                return 1

            except Exception as e:
                return str(e)
        else:
            return 0


    def make_reservation(self, insert_data):

        print(type(insert_data))
        if self._db_check != 1:
            conn = sqlite3.connect(self.base_path)
            cursor = conn.cursor()
            print(insert_data)

            try:
                cursor.executemany("INSERT INTO reserve VALUES (null,?,?,?,?,?,?)", insert_data)
                conn.commit()
                conn.close()
                return 1

            except Exception as e:
                return str(e)


    def deactivate_reservation(self, comb_id, phone_number, active_stamp=0):
        conn = sqlite3.connect(self.base_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE reserve SET active_stamp=:as WHERE comb_id=:comb_id AND phone_number=:phone_number",
                {'comb_id': comb_id, 'phone_number': phone_number, 'as': active_stamp}
                )
            
            conn.commit()
            conn.close()
            return 1
        except Exception as e:
            return str(e)



    def get_reservation(self, comb_id, phone_number):
        print("IN GET RESERV ", comb_id, phone_number)
        try:
            str(comb_id)
        except Exception as e:
            return str(e)

        if comb_id != None:
            conn = sqlite3.connect(self.base_path, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM reserve WHERE phone_number=?", (phone_number, ))
                db_field = cursor.fetchone()
                conn.close()

            except Exception as e:
                conn.close()
                return None
            
        
            print("from db: ", db_field)
            return db_field