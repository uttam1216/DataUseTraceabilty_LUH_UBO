import os
import pandas as pd
import uuid
import datetime
from src.utils.util import debug, registered_data_columns, transferred_data_columns, get_prefix, transact_with_db, \
    flag_transact_with_db
import psycopg2
from sqlalchemy import create_engine
from datetime import datetime as dt


# new func to interact with DB
def test_conn():
    conn = None
    cur = None
    try:
        # creating a connection using sqlalchemy
        engine = create_engine('postgresql://smashhit_user:smashhit_pwd@localhost:5432/smashhit')
        # loading in pandas dataframe
        df = pd.read_sql_query("select * from records", con=engine)
        # print('data from dataframe is: ')
        # print(df)
        # other way of making connection
        conn = psycopg2.connect(host='localhost', dbname='smashhit', user='smashhit_user', password='smashhit_pwd',
                                port=5432)
        cur = conn.cursor()
        # spatial_ref_sys, planet_osm_point, planet_osm_line, planet_osm_polygon, planet_osm_roads are tables
        print('Connection established and cursor active')
        # delete all pre-existing records of the table records
        # cur.execute('DELETE FROM public.records;')
        cur.execute('DELETE FROM public.registered_data;')
        cur.execute('DELETE FROM public.transferred_data;')
        print('deleted all records of table records')
        conn.commit()
        # insert 1 record of manager in records table
        tbl = "records"
        mgr = 'manager'
        # query_string = f"Insert into {tbl} values ('{mgr}','manager_uri'," \
        #               f"'../../src/keys/manager_uri_ed25519'," \
        #               f"'../../src/keys/manager_uri_ed25519.pub');".format()
        # cur.execute(query_string)
        # cur.execute("Insert into public.records values ('manager','manager_uri','../../src/keys/manager_uri_ed25519',"
        #            "'../../src/keys/manager_uri_ed25519.pub');")
        # conn.commit()
        cur.execute('SELECT * FROM public.records;')
        all_records = cur.fetchall()
        print('number of rows in records table is:', len(all_records))
        # i = 0
        for record in all_records:
            print(record[0])
        '''
        # inserting data in table from a dataframe
        new_row = {'actor': 'UBO_U_sender', 'uniform_resource_identifier': '8039ace8-1ef8-11ed-ab79-9fab5267d284', 
        'path_to_private_key': '../../src/keys/8039ace8-1ef8-11ed-ab79-9fab5267d284_ed25519', 
        'path_to_public_key': '../../src/keys/8039ace8-1ef8-11ed-ab79-9fab5267d284_ed25519.pub'}
        df = df.append(new_row, ignore_index=True)
        print(df)
        df.to_sql(name='public.records', con=engine, if_exists='append', index=False)
        # again reading in data from the table into df
        df = pd.read_sql_query("select * from records", con=engine)
        print('data from dataframe again is: ')
        print(df)
        '''
    except Exception as ex:
        print(ex)
    finally:
        if conn is not None:
            conn.close()
        if cur is not None:
            cur.close()


def _get_data_id(hash_data,
                 log_path_registered_data='../../src/utils/registered_data.csv'):
    """
    function that extracts the uniform_resource_identifier (data_id) for the hash_data
    :param hash_data:
    :return: str
    """
    # start of changes by Uttam on 16 Sep to transact with DB
    if flag_transact_with_db:
        obj = transact_with_db()
        registered_data_df = obj.fetch_records_in_df('registered_data')
    else:
        # end of changes by Uttam on 16 Sep to transact with DB
        registered_data_df = pd.read_csv(log_path_registered_data)
    indexes = registered_data_df.index[str(hash_data) == registered_data_df['hash_data']]
    if len(indexes) == 0:
        raise ValueError('The data you are looking for does not exists, hash not registered')
    index = indexes[-1]
    uniform_resource_identifier = registered_data_df.loc[index, 'uniform_resource_identifier']
    return uniform_resource_identifier


# class with functions to transact with data from the database/csv files
def onboard(actor):
    already_present = False
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

    module_record = {}
    # verify if the actor is already present in the lis of actors
    if actor in records_df['actor'].to_list():
        index = records_df.index[records_df["actor"] == actor][0]
        module_record = records_df.iloc[index]
        already_present = True

    response = {"already_present": already_present, "module_record": module_record}
    return response


class DataProcessingLogs:
    def __init__(self, log_path_registered_data, log_path_transferred_data):
        self.log_path_registered_data = log_path_registered_data
        self.log_path_transferred_data = log_path_transferred_data
        self.registered_data_columns = registered_data_columns
        self.transferred_data_columns = transferred_data_columns
        self.registered_data_df = pd.DataFrame(columns=self.registered_data_columns)
        self.transferred_data_df = pd.DataFrame(columns=self.transferred_data_columns)
        if not os.path.exists(self.log_path_registered_data):
            self.registered_data_df.to_csv(self.log_path_registered_data, index=False)
        if not os.path.exists(self.log_path_transferred_data):
            self.transferred_data_df.to_csv(self.log_path_transferred_data, index=False)
            # for the moment we use a pandas dataframe as storage which we keep in memory and also store as csv

    # function that performs the actual data transfer to teh database/csv files
    def register_data(self, smashhit_id, hash_data, signed_hash, consent_id, contract_id, fingerprint, origin,
                      creation_time, expiration_time):
        if debug:
            uniform_resource_identifier = f'{hash_data}_uri'
        else:
            uniform_resource_identifier = uuid.uuid1()
        # change done on 19 sep by uttam
        if not isinstance(hash_data, str):
            hash_data = hash_data.decode("utf-8")
        data = {
            'smashhit_id': smashhit_id,
            'uniform_resource_identifier': uniform_resource_identifier,
            'hash_data': hash_data,
            'signed_hash': signed_hash,
            'consent_id': consent_id,
            'contract_id': contract_id,
            'origin': origin,
            'creation_time': creation_time,
            'expiration_time': expiration_time,
            'fingerprint': fingerprint
        }
        self.registered_data_df = pd.DataFrame(columns=self.registered_data_columns)
        self.registered_data_df = self.registered_data_df.append(data, ignore_index=True)

        # start of changes by Uttam on 16 Sep to transact with DB
        if flag_transact_with_db:
            obj = transact_with_db()
            current_log_df = obj.fetch_records_in_df('registered_data')
        else:
            # end of changes by Uttam on 16 Sep to transact with DB
            # Assuming that the current log in log_path is in csv
            current_log_df = pd.read_csv(self.log_path_registered_data)
        ''' Change in logic on 23rd June'22, contract_id to be made optional.
        # we verify if the data already exists for same contract id:
        indexes = current_log_df.index[current_log_df.contract_id == contract_id]
        if len(indexes) != 0:
            # same contract id already registered, we raise an exception
            raise ValueError("Data having same contract id is already registered.")
        '''

        # we verify if the data already exists with same consent id and contract id:
        # 23rd June'22: Allowing multiple data hash with same consent & contract be present
        indexes = current_log_df.index[(current_log_df.consent_id == consent_id) &
                                       (str(current_log_df.contract_id).strip() == str(contract_id).strip()) &
                                       (current_log_df.hash_data == hash_data)]
        if len(indexes) != 0:
            # same consent id and contract id already registered, we raise an exception
            raise ValueError("Data having same consent id, contract id and hash data already registered.")

        # put check that one(consent) to many(contract) relationship exist but not vice-versa
        if str(contract_id).strip() != '':
            selective_current_log_df = current_log_df.loc[(current_log_df.contract_id == contract_id)]
            if not selective_current_log_df.empty:
                if consent_id not in list(selective_current_log_df['consent_id'].unique()):
                    # another consent id is present against the contract which is being entered with current consent
                    raise ValueError(
                        "Another consent id exists in records against the contract currently being fed.")

        indexes = current_log_df.index[current_log_df['hash_data'] == str(hash_data)]
        if len(indexes) != 0:
            # hash_data already present, we raise an exception
            uri = list(current_log_df.query('hash_data==@hash_data')['uniform_resource_identifier'])[0]
            raise ValueError(f"Data with same hash_data already registered against following uri: {uri}".format())

        try:
            merged_log_df = current_log_df.append(self.registered_data_df, ignore_index=True)
            # start of changes by Uttam on 16 Sep to transact with DB
            if flag_transact_with_db:
                obj = transact_with_db()
                obj.insert_values_in_registered_data(data)
            else:
                # end of changes by Uttam on 16 Sep to transact with DB
                merged_log_df.to_csv(self.log_path_registered_data, index=False)
        except ValueError as e:
            message = f'existing registered data with different format with respect to new ones.\n{e}'
            return message

        return uniform_resource_identifier

    def check_actor_name(self, actor_name):
        try:
            if flag_transact_with_db:
                obj = transact_with_db()
                records_df = obj.fetch_records_in_df('records')
            else:
                # end of changes by Uttam on 16 Sep to transact with DB
                path_to_records_table = f"{get_prefix()}src/utils/records_table.csv"
                records_df = pd.read_csv(path_to_records_table)
            indexes = records_df.index[records_df['actor'] == str(actor_name)]
            if len(indexes) == 0:
                record = {'actor': '',
                          'uniform_resource_identifier': '',
                          'path_to_private_key': '',
                          'path_to_public_key': ''}
                return record
            else:
                sel_records_df = records_df.loc[records_df['actor'] == str(actor_name)]
                if sel_records_df.empty:
                    record = {'actor': '',
                              'uniform_resource_identifier': '',
                              'path_to_private_key': '',
                              'path_to_public_key': ''}
                else:
                    record = {'actor': sel_records_df['actor'].values[0],
                              'uniform_resource_identifier': str(
                                  sel_records_df['uniform_resource_identifier'].values[0]),
                              'path_to_private_key': sel_records_df['path_to_private_key'].values[0],
                              'path_to_public_key': sel_records_df['path_to_public_key'].values[0]}
                return record
        except ValueError as e:
            return {'Error': e.args[0]}

    def get_consent_data_trace(self, consent_id):
        # the function returns a joined table of registered data and transferred data on data uri based on consent id

        try:
            # start of changes by Uttam on 16 Sep to transact with DB
            if flag_transact_with_db:
                obj = transact_with_db()
                registered_data_df = obj.fetch_records_in_df('registered_data')
                transferred_data_df = obj.fetch_records_in_df('transferred_data')
            else:
                # end of changes by Uttam on 16 Sep to transact with DB
                registered_data_df = pd.read_csv(self.log_path_registered_data)
                transferred_data_df = pd.read_csv(self.log_path_transferred_data)
            """
            result_df = registered_data_df.loc[registered_data_df['consent_id'] == str(consent_id)]\
                .join(transferred_data_df.set_index('uniform_resource_identifier'), on='uniform_resource_identifier')
            """
            indexes = registered_data_df.index[registered_data_df['consent_id'] == str(consent_id)]
            if len(indexes) == 0:
                raise ValueError('No registered data with such a consent id')
            data_trace_df = pd.DataFrame(columns=self.transferred_data_columns)
            # if 'contract_id' not in data_trace_df:
            #     data_trace_df['contract_id'] = ''
            if 'consent_id' not in data_trace_df:
                data_trace_df['consent_id'] = ''
            # if 'contract_id' not in transferred_data_df:
            #     transferred_data_df['contract_id'] = ''
            if 'consent_id' not in transferred_data_df:
                transferred_data_df['consent_id'] = ''
            for i in range(len(indexes)):
                data_id = registered_data_df.loc[indexes[i], 'uniform_resource_identifier']
                # contract_id = registered_data_df.loc[indexes[i], 'contract_id']
                consent_id = registered_data_df.loc[indexes[i], 'consent_id']
                # transferred_data_df.loc[
                #     transferred_data_df['uniform_resource_identifier'] == data_id, 'contract_id'] = contract_id
                transferred_data_df.loc[
                    transferred_data_df['uniform_resource_identifier'] == data_id, 'consent_id'] = consent_id
                row = transferred_data_df.loc[transferred_data_df['uniform_resource_identifier'] == data_id]
                data_trace_df = data_trace_df.append(row, ignore_index=True)
            lst_col = self.transferred_data_columns
            # if 'consent_id' in lst_col:
            #    lst_col.remove('consent_id')  # not needed as this is what was input for in this function
            if 'consent_id' not in lst_col:
                lst_col.append('consent_id')
            # if 'contract_id' not in lst_col:
            #     lst_col.append('contract_id')
            data_trace_df = pd.DataFrame(data_trace_df, columns=lst_col)
            data_trace_df = data_trace_df.reset_index(drop=True)
            data_trace_df = data_trace_df.fillna('')
            trace_in_json = data_trace_df.to_dict()
            return trace_in_json
        except ValueError as e:
            return e.args[0]

    def get_contract_data_trace(self, contract_id):
        # the function returns a joined table of registered data and transferred data on data uri based on contract id

        try:
            # start of changes by Uttam on 16 Sep to transact with DB
            if flag_transact_with_db:
                obj = transact_with_db()
                registered_data_df = obj.fetch_records_in_df('registered_data')
                transferred_data_df = obj.fetch_records_in_df('transferred_data')
            else:
                # end of changes by Uttam on 16 Sep to transact with DB
                registered_data_df = pd.read_csv(self.log_path_registered_data)
                transferred_data_df = pd.read_csv(self.log_path_transferred_data)
            """
            result_df = registered_data_df.loc[registered_data_df['contract_id'] == str(contract_id)]\
                .join(transferred_data_df.set_index('uniform_resource_identifier'), on='uniform_resource_identifier')
            """
            indexes = registered_data_df.index[registered_data_df['contract_id'] == str(contract_id)]
            if len(indexes) == 0:
                raise ValueError('No registered data with such a contract id')
            data_trace_df = pd.DataFrame(columns=self.transferred_data_columns)
            if 'consent_id' not in data_trace_df:
                data_trace_df['consent_id'] = ''
            if 'contract_id' not in data_trace_df:
                data_trace_df['contract_id'] = ''
            if 'contract_id' not in transferred_data_df:
                transferred_data_df['contract_id'] = ''
            if 'consent_id' not in transferred_data_df:
                transferred_data_df['consent_id'] = ''
            for i in range(len(indexes)):
                data_id = registered_data_df.loc[indexes[i], 'uniform_resource_identifier']
                consent_id = registered_data_df.loc[indexes[i], 'consent_id']
                contract_id = registered_data_df.loc[indexes[i], 'contract_id']
                transferred_data_df.loc[
                    transferred_data_df['uniform_resource_identifier'] == data_id, 'consent_id'] = consent_id
                transferred_data_df.loc[
                    transferred_data_df['uniform_resource_identifier'] == data_id, 'contract_id'] = contract_id
                row = transferred_data_df.loc[transferred_data_df['uniform_resource_identifier'] == data_id]
                data_trace_df = data_trace_df.append(row, ignore_index=True)
            lst_col = self.transferred_data_columns
            # if 'contract_id' in lst_col:
            #     lst_col.remove('contract_id')  # not needed as this is what was input for in this function
            if 'contract_id' not in lst_col:
                lst_col.append('contract_id')
            if 'consent_id' not in lst_col:
                lst_col.append('consent_id')
            data_trace_df = pd.DataFrame(data_trace_df, columns=lst_col)
            data_trace_df = data_trace_df.reset_index(drop=True)
            data_trace_df = data_trace_df.fillna('')
            trace_in_json = data_trace_df.to_dict()
            return trace_in_json
        except ValueError as e:
            return e.args[0]

    # function that performs the entry of data transfer in the database/csv
    def log_data_transfer(self, uniform_resource_identifier, sender_id, receiver_id,
                          signature_of_sender, signature_of_receiver=None):
        try:
            if signature_of_sender is None and signature_of_receiver is None:
                raise ValueError("Either sender or receiver signature needs to be supplied")
            # We store that information along with the timestamp
            if signature_of_receiver is None:
                # verify if data has been registered
                # start of changes by Uttam on 16 Sep to transact with DB
                if flag_transact_with_db:
                    obj = transact_with_db()
                    current_log_df = obj.fetch_records_in_df('registered_data')
                else:
                    # end of changes by Uttam on 16 Sep to transact with DB
                    current_log_df = pd.read_csv(self.log_path_registered_data)
                record_indexes = current_log_df.index[
                    (current_log_df['uniform_resource_identifier'] == str(uniform_resource_identifier))]
                if len(record_indexes) == 0:
                    raise ValueError('The data you want to transfer has not been registered, pls register first.')

                # transfer of the data
                data = {
                    'uniform_resource_identifier': uniform_resource_identifier,
                    'sender_id': sender_id,
                    'receiver_id': receiver_id,
                    'signature_of_sender': signature_of_sender,
                    'signature_of_receiver': '' if signature_of_receiver is None else signature_of_receiver,
                    'transfer_date_time': datetime.datetime.now(),
                    'confirm_date_time': '',
                }

                try:
                    # start of changes by Uttam on 16 Sep to transact with DB
                    if flag_transact_with_db:
                        obj = transact_with_db()
                        obj.insert_values_in_transferred_data(data)
                    else:
                        # end of changes by Uttam on 16 Sep to transact with DB
                        self.transferred_data_df = pd.DataFrame(columns=self.transferred_data_columns)
                        self.transferred_data_df = self.transferred_data_df.append(data, ignore_index=True)
                        current_log_df = pd.read_csv(self.log_path_transferred_data)
                        merged_log_df = current_log_df.append(self.transferred_data_df, ignore_index=True)
                        merged_log_df.to_csv(self.log_path_transferred_data, index=False)
                    return ""
                except ValueError as e:
                    raise ValueError(f'existing transferred data is in different format than the new ones.\n{e}')

            # receiving mode
            try:
                # start of changes by Uttam on 16 Sep to transact with DB
                if flag_transact_with_db:
                    obj = transact_with_db()
                    current_log_df = obj.fetch_records_in_df('transferred_data')
                else:
                    # end of changes by Uttam on 16 Sep to transact with DB
                    current_log_df = pd.read_csv(self.log_path_transferred_data)
            except:
                # will do the following if the csv file is not there
                self.transferred_data_df.to_csv(self.log_path_transferred_data, index=False)
                current_log_df = self.transferred_data_df
            record_indexes = current_log_df.index[
                (current_log_df['uniform_resource_identifier'] == str(uniform_resource_identifier)) &
                (current_log_df['sender_id'] == str(sender_id)) &
                (current_log_df['receiver_id'] == str(receiver_id))]
            if len(record_indexes) == 0:
                raise ValueError('The data you are looking for is not present, verify the data_uri, sender_id and '
                                 'receiver_id')
            # start of changes by Uttam on 16 Sep to transact with DB
            if flag_transact_with_db:
                obj = transact_with_db()
                obj.update_values_in_transferred_data({'signature_of_receiver': signature_of_receiver,
                                                       'confirm_date_time': datetime.datetime.now(),
                                                       'uniform_resource_identifier': str(uniform_resource_identifier),
                                                       'sender_id': str(sender_id),
                                                       'receiver_id': str(receiver_id)})
            else:
                # end of changes by Uttam on 16 Sep to transact with DB
                record_index = record_indexes[-1]
                current_log_df.loc[record_index, 'signature_of_receiver'] = signature_of_receiver
                current_log_df.loc[record_index, 'confirm_date_time'] = datetime.datetime.now()
                current_log_df.to_csv(self.log_path_transferred_data, index=False)
            return ""
        except ValueError as e:
            return e.args[0]


if __name__ == "__main__":
    test_conn()
