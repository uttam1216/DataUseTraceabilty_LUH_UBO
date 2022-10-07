import os
from src.utils import encryption_module as em
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import requests

# debug = True  # if we want to test the Modules and Manager APIs calls
debug = False  # if we want to run unit tests
calls_ready = True
flag_transact_with_db = False


url_to_manager = 'http://localhost:5000'  # local laptop/client machine
# url_to_manager = 'http://smashhit.l3s.uni-hannover.de'  # L3S
# url_to_manager = 'https://smashhit.ari-mobility.eu/api/traceability' # ATOS

# manager name
manager_name = "manager" if url_to_manager == 'http://localhost:5000' else "remote_manager"
manager_copy = "manager_copy" if url_to_manager == 'http://localhost:5000' else "remote_manager_copy"


# function to fetch the prefix of folder path
def get_prefix():
    root = 'src'
    pref = ''
    while not os.path.exists(f'{pref}{root}'):
        pref = f'../{pref}'
    return pref


prefix = get_prefix()
log_path_registered_data = f'{prefix}src/utils/registered_data.csv'
log_path_transferred_data = f'{prefix}src/utils/transferred_data.csv'

registered_data_columns = ['smashhit_id', 'uniform_resource_identifier', 'hash_data', 'signed_hash',
                           'consent_id', 'contract_id', 'fingerprint', 'origin', 'creation_time', 'expiration_time']
transferred_data_columns = ['uniform_resource_identifier', 'sender_id', 'receiver_id',
                            'signature_of_sender', 'signature_of_receiver', 'transfer_date_time', 'confirm_date_time']


# class with functions to transact with database
class transact_with_db:
    def __init__(self):
        # creating a connection to DB using sqlalchemy
        self.engine = create_engine('postgresql://****:****@localhost:5432/smashhit')
        # creating a connection to DB using psycopg2
        self.conn = psycopg2.connect(host='localhost', dbname='smashhit', user='****', password='****',
                                     port=5432)
        self.cur = self.conn.cursor()

    def fetch_records_in_df(self, tbl_name):
        try:
            # loading in pandas dataframe
            df = pd.read_sql_query(f"select * from {tbl_name};".format(), con=self.engine)
            # print('data from dataframe is: ')
            # print(df)
            return df
        except Exception as ex:
            print(ex)
        finally:
            if self.conn is not None:
                self.conn.close()
            if self.cur is not None:
                self.cur.close()

    def fetch_records(self, tbl_name, actor):
        try:
            # loading in pandas dataframe
            # df = pd.read_sql_query(f"select * from public.{tbl_name} where actor = {actor};".format(), con=self.engine)
            self.cur.execute(f"select * from {tbl_name} where actor = '{actor}';".format())
            all_records = self.cur.fetchall()
            # print('data from dataframe is: ')
            # print(df)
            # for record in all_records:
            #    print(record[0])
            return all_records
        except Exception as ex:
            print(ex)
        finally:
            if self.conn is not None:
                self.conn.close()
            if self.cur is not None:
                self.cur.close()

    def insert_values_in_records(self, records_dict):
        try:
            query_string = f"Insert into records values ('{records_dict['actor']}'," \
                           f"'{records_dict['uniform_resource_identifier']}'," \
                           f"'{records_dict['path_to_private_key']}'," \
                           f"'{records_dict['path_to_public_key']}'," \
                           f" current_timestamp);".format()
            self.cur.execute(query_string)
            self.conn.commit()
        except Exception as ex:
            print(ex)
        finally:
            if self.conn is not None:
                self.conn.close()
            if self.cur is not None:
                self.cur.close()

    def insert_values_in_registered_data(self, registered_data_dict):
        try:
            query_string = f"Insert into registered_data values ('{registered_data_dict['smashhit_id']}'," \
                           f"'{registered_data_dict['uniform_resource_identifier']}','{registered_data_dict['hash_data']}'," \
                           f"'{registered_data_dict['signed_hash']}','{registered_data_dict['consent_id']}'," \
                           f"'{registered_data_dict['contract_id']}','{registered_data_dict['origin']}'," \
                           f"'{registered_data_dict['creation_time']}','{registered_data_dict['expiration_time']}', " \
                           f"'{registered_data_dict['fingerprint']}', '', current_timestamp, NULL );".format()
            self.cur.execute(query_string)
            self.conn.commit()
        except Exception as ex:
            print(ex)
        finally:
            if self.conn is not None:
                self.conn.close()
            if self.cur is not None:
                self.cur.close()

    def insert_values_in_transferred_data(self, transferred_data_dict):
        try:
            query_string = f"Insert into transferred_data values ('{transferred_data_dict['uniform_resource_identifier']}'," \
                           f"'{transferred_data_dict['sender_id']}','{transferred_data_dict['receiver_id']}'," \
                           f"'{transferred_data_dict['signature_of_sender']}', " \
                           f"'{transferred_data_dict['signature_of_receiver']}', " \
                           f" current_timestamp, " \
                           f" NULL);".format()
            self.cur.execute(query_string)
            self.conn.commit()
        except Exception as ex:
            print(ex)
        finally:
            if self.conn is not None:
                self.conn.close()
            if self.cur is not None:
                self.cur.close()

    def update_values_in_transferred_data(self, transferred_data_dict):
        try:
            query_string = f"UPDATE transferred_data SET signature_of_receiver = '{transferred_data_dict['signature_of_receiver']}', " \
                           f" confirm_date_time = current_timestamp WHERE" \
                           f" uniform_resource_identifier = '{transferred_data_dict['uniform_resource_identifier']}' " \
                           f" AND sender_id = '{transferred_data_dict['sender_id']}' " \
                           f" AND receiver_id = '{transferred_data_dict['receiver_id']}';".format()
            self.cur.execute(query_string)
            self.conn.commit()
        except Exception as ex:
            print(ex)
        finally:
            if self.conn is not None:
                self.conn.close()
            if self.cur is not None:
                self.cur.close()

    def delete_values_in_tbl(self, tbl_name):
        try:
            # delete all pre-existing records of the table records
            query_string = f"DELETE FROM {tbl_name};".format()
            self.cur.execute()
            print('deleted all records of table records')
            self.conn.commit()
            # insert 1 record of manager in records table
        except Exception as ex:
            print(ex)
        finally:
            if self.conn is not None:
                self.conn.close()
            if self.cur is not None:
                self.cur.close()


# function to fetch the record
def get_record(actor, access_token="None"):
    """
    from src.utils import encryption_module as em
    import pandas as pd
    import os
    """
    path_to_records_table = "../../src/utils/records_table.csv"
    table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']

    # start of changes by Uttam on 29th Sept
    if access_token != 'None':
        # add a 'remote_' before actor name change 30 Sept by Uttam
        url_to_fetch_records = url_to_manager + f'/check_actor/remote_{actor}'.format()
        headers = {'x-auth-token': access_token}
        # r = requests.get(url=url_to_fetch_records, headers=headers)
        if url_to_manager == 'https://smashhit.ari-mobility.eu/api/traceability':
            r = requests.get(url=url_to_fetch_records, headers=headers)
        else:
            r = requests.get(url=url_to_fetch_records)
        r = r.json()
        if r is None:
            return None
        elif r['actor'] == '':
            return None
        else:
            return r


    # end of changes by Uttam on 29th Sept

    # start of changes by Uttam on 16 Sep to transact with DB
    if flag_transact_with_db:
        obj = transact_with_db()
        # fetching records from records table of the DB
        all_records = obj.fetch_records('records', actor)
        if len(all_records) > 0:
            for record in all_records:
                # converting the tuple received into dict for future use
                new_actor = {'actor': record[0], 'uniform_resource_identifier': record[1],
                             'path_to_private_key': record[2], 'path_to_public_key': record[3]}
                return new_actor
        else:
            return None

    else:
        # end of changes by Uttam on 16 September
        if not os.path.exists(path_to_records_table):
            records_df = pd.DataFrame(columns=table_columns)
        else:
            records_df = pd.read_csv(path_to_records_table)
        if actor in records_df['actor'].to_list():
            index = records_df.index[records_df["actor"] == actor][0]
            new_actor = records_df.iloc[index]
            new_actor = new_actor.fillna('').to_dict()
            return new_actor

    return None


def create_record(actor):
    record = get_record(actor)
    if record is None:
        path_to_records_table = "../../src/utils/records_table.csv"
        table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
        if not os.path.exists(path_to_records_table):
            records_df = pd.DataFrame(columns=table_columns)
        else:
            records_df = pd.read_csv(path_to_records_table)
        # the case if the actor is not present and has to be created
        import uuid

        path_to_private_keys = f'{prefix}src/keys'
        path_to_public_keys = f'{prefix}src/keys'
        if debug:
            uniform_resource_identifier = f'{actor}_uri'
        else:
            uniform_resource_identifier = uuid.uuid1()
        private_key_filename = f'{uniform_resource_identifier}_ed25519'
        path_to_private_key = f'{path_to_private_keys}/{private_key_filename}'
        public_key_filename = f'{uniform_resource_identifier}_ed25519.pub'
        path_to_public_key = f'{path_to_public_keys}/{public_key_filename}'
        # creation of keys
        private_key = em.generate_private_key()
        em.save_private_key(private_key, path_to_private_key)
        public_key = em.generate_public_key(private_key)
        em.save_public_key(public_key, path_to_public_key)

        # if actor is local manager, we should create a local copy of the manager
        if actor == "manager":
            em.save_public_key(public_key, f"{get_prefix()}src/keys/manager_copy_public_key.pub")

        # insertion of the new record in table
        new_record = {'actor': actor, 'uniform_resource_identifier': str(uniform_resource_identifier),
                      'path_to_private_key': path_to_private_key, 'path_to_public_key': path_to_public_key}
        # ignore_index=True to avoid thinking about the index
        # start of changes by Uttam on 16 Sep to transact with DB
        if flag_transact_with_db:
            obj = transact_with_db()
            obj.insert_values_in_records(new_record)
        else:
            # end of changes by Uttam on 16 Sep to transact with DB
            records_df = records_df.append(new_record, ignore_index=True)
            records_df = pd.DataFrame(records_df, columns=table_columns)
            records_df.to_csv(path_to_records_table, index=False)
        return new_record
    return record


# function for boarding of a new company on smashhit's traceability module - still under development
def onboard(name, url):
    from requests import post

    # create and insert the actor inside the module or get existing actor
    result = create_record(name)
    new_data = result.copy()
    new_data["path_to_private_key"] = ""
    new_data["path_to_public_key"] = ""

    if url_to_manager == 'http://smashhit.l3s.uni-hannover.de' or url_to_manager == 'http://localhost:5000':
        url = url_to_manager
    else:
        url = 'http://smashhit.l3s.uni-hannover.de'
    # insert the new if not existing yet
    ret = post(url=f'{url}/onboard', json=new_data)
    response = ret.text
    if ret.status_code == 200:  # 200 means new actor, 201 means old actor
        # we send the public key of the module to the manager
        y = open(result["path_to_public_key"], 'rb')
        files = {'file': y}

        x = post(url=f'{url}/key_file', files=files).json()

    # create manager actor with path to the public key corresponding to the existing public key.
    path_to_manager_public_key = f"{get_prefix()}src/keys/{manager_copy}_public_key.pub"
    manager_record = {'actor': manager_name, 'uniform_resource_identifier': "",
                      'path_to_private_key': "", 'path_to_public_key': path_to_manager_public_key}

    path_to_records_table = f"{get_prefix()}src/utils/records_table.csv"
    table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
    if not os.path.exists(path_to_records_table):
        records_df = pd.DataFrame(columns=table_columns)
    else:
        # start of changes by Uttam on 16 Sep to transact with DB
        if flag_transact_with_db:
            obj = transact_with_db()
            records_df = obj.fetch_records_in_df('records')
        else:
            # end of changes by Uttam on 16 Sep to transact with DB
            records_df = pd.read_csv(path_to_records_table)

    if manager_name not in records_df['actor'].to_list():
        # start of changes by Uttam on 16 Sep to transact with DB
        if flag_transact_with_db:
            obj = transact_with_db()
            obj.insert_values_in_records(manager_record)
        else:
            # end of changes by Uttam on 16 Sep to transact with DB
            # insert the manager, ignore_index=True to avoid thinking about the index
            records_df = records_df.append(manager_record, ignore_index=True)
            records_df = pd.DataFrame(records_df, columns=table_columns)
            records_df.to_csv(path_to_records_table, index=False)

    # print the response for giving the outcome of onboard process
    print(response)

    return result
