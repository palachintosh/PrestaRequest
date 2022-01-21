import os
import os.path
import sqlite3
from sqlite3.dbapi2 import connect
# from bikes_monitoring.tasks import auto_delete_reserve


class ReserveBikes:
    def __init__(self, name=None):

        self.name = name
        
        if self.name == None:
            self.name = 'reserved_bikes.db'

        self.base_path = os.path.dirname(os.path.abspath(__file__)) + '/' + self.name
        self.create_db()


    def _db_check(self):
        try:
            conn = sqlite3.connect('file:{}?mode=rw'.format(self.base_path), uri=True)
            print("Reading database..\n", "Done")
            conn.close()
            return 1

        except Exception as e:
            print("Error: unable to open database. DB does not exist!")
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
                task_pid text,
                comb_id text,
                reference text,
                qty INTEGER,
                permanent_r INTEGER,
                active_stamp INTEGER)""")
                
                conn.commit()
                conn.close()

                return 1

            except Exception as e:
                return str(e)
        else:
            return 0


    def make_reservation(self, insert_data):
        import datetime
        print(type(insert_data))
        if self._db_check() != 1:
            return 0

        conn = sqlite3.connect(self.base_path)
        cursor = conn.cursor()
        print(insert_data)

        try:
            cursor.executemany("INSERT INTO reserve VALUES (null,?,?,?,?,?,?,?,?)", insert_data)
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
        if comb_id is not None:
            conn = sqlite3.connect(self.base_path, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM reserve WHERE phone_number=?;", (phone_number, ))
                db_field = cursor.fetchone()
                conn.close()

            except Exception as e:
                conn.close()
                return None
            
            return db_field


    def get_res_dict(self, comb_id):
        if comb_id is not None:
            conn = sqlite3.connect(self.base_path, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM reserve WHERE comb_id=? AND active_stamp=1", (comb_id, ))
                db_field = cursor.fetchall()
                conn.close()

            except Exception as e:
                conn.close()
                return None

            return db_field


    def add_task_id(self, task_id, reserve_id):
        conn = sqlite3.connect(self.base_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE reserve SET task_pid=:task_id WHERE id=:reserve_id",
                {'reserve_id':reserve_id, 'task_id': task_id}
                )
            conn.commit()
            conn.close()
            return 1

        except Exception as e:
            conn.close()
            return None


