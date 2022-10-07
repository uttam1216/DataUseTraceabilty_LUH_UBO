import time
import os
import threading
import logging
import requests
import pandas as pd
from src.utils.util import transact_with_db, flag_transact_with_db


# defining class with methods to test the API's performance
class test_functionalities():
    # test register data API's performance
    def test_register_data_api(self, consent_id_num):
        global response_uri_lst
        if isinstance(consent_id_num, int):
            consent_id_num = consent_id_num
        else:
            consent_id_num = consent_id_num[0]
        # defining dummy data which will be registered
        consent_id = 'cdb_' + str(consent_id_num)
        contract_id = consent_id + '_contract'
        hash = consent_id + '_hash'
        origin = consent_id + '_origin'
        fingerprint = consent_id + "_fingerprint"
        data = {
            "access_token": "a_t",
            "consent_id": consent_id,
            "contract_id": contract_id,
            "creation_time": "2022-09-22",
            "expiration_time": "2023-06-24",
            "fingerprint": fingerprint,
            "hash": hash,
            "origin": origin,
        }

        headers = requests.utils.default_headers()
        user_agent = 'UserAgent' + str(consent_id_num)
        headers.update(
            {
                'User-Agent': user_agent,
                'Connection': 'Keep-Alive',
            }
        )
        try:
            r = requests.post(url='http://localhost:5001/register', json=data, headers=headers)
            # print(r)
            response_data = r.json()
            response_data['hash'] = hash
            if response_data['ERROR'] != '':
                print('error')
            # uri_temp = str(response_data['uri']) if response_data['ERROR'] == '' else ''
            response_uri_lst.append(response_data)
        except Exception as ex:
            print(ex)

    # test initiate data transfer API's performance
    def test_init_data_transfer_api(self):
        global response_uri_lst, response_data_transfer_lst
        ctr = 0  # counter of response elements
        for response_dict in response_uri_lst:
            if response_dict['ERROR'] == '':
                ctr += 1
                receiver_name = 'VW_Receiver'
                data = {
                    "access_token": "a_t",
                    "receiver_name": receiver_name,
                    "uri": response_dict['uri']
                }
                headers = requests.utils.default_headers()
                user_agent = 'UserAgent' + str(ctr)
                headers.update(
                    {
                        'User-Agent': user_agent,
                        'Connection': 'Keep-Alive',
                    }
                )
                try:
                    r = requests.post(url='http://localhost:5001/init_transfer', json=data, headers=headers)
                    response_data = r.json()
                    response_data['hash'] = response_dict['hash']
                    response_data['uri'] = response_dict['uri']
                    response_data_transfer_lst.append(response_data)
                except Exception as ex:
                    print(ex)

    # test confirm data receipt API's performance
    def test_confirm_data_receipt_api(self, response_data_transfer_lst):
        # global response_data_transfer_lst, response_confirm_data_receipt_lst
        global response_confirm_data_receipt_lst

        # response_data_transfer_df = pd.read_csv("../src/utils/transferred_data.csv")

        ctr = 0  # counter of response elements
        for response_dict in response_data_transfer_lst:
            if 1 == 1:
                ctr += 1
                data = {
                    "access_token": "a_t",
                    "hash": response_dict['hash'],
                    "sender_id": response_dict['sender_id'],
                    "signature_of_sender": response_dict['signature_of_sender'],
                    "uri": response_dict['uri']
                }
                headers = requests.utils.default_headers()
                user_agent = 'UserAgent' + str(ctr)
                headers.update(
                    {
                        'User-Agent': user_agent,
                        'Connection': 'Keep-Alive',
                    }
                )
                try:
                    r = requests.post(url='http://localhost:5001/confirm_transfer', json=data, headers=headers)
                    response_data = r.json()
                    response_data['hash'] = response_dict['hash']
                    response_confirm_data_receipt_lst.append(response_data)
                except Exception as ex:
                    print(ex)

    # test get data trace based on consent id API's performance
    def test_get_data_trace_consent_api(self, consent_id_num):
        global response_data_trace_consent_lst
        # defining dummy data which will be registered
        consent_id = 'cdb_' + str(consent_id_num)  # if consent_id_num is 1 then consent_id = c_001
        data = {
            "access_token": "a_t",
            "consent_id": consent_id
        }

        headers = requests.utils.default_headers()
        user_agent = 'UserAgent' + str(consent_id_num)
        headers.update(
            {
                'User-Agent': user_agent,
                'Connection': 'Keep-Alive',
            }
        )
        try:
            r = requests.post(url='http://localhost:5001/consent_trace', json=data, headers=headers)
            response_data = r.json()
            response_data_trace_consent_lst.append(response_data)
        except Exception as ex:
            print(ex)

    # test get data trace based on contract id API's performance
    def test_get_data_trace_contract_api(self, contract_id_num):
        global response_data_trace_contract_lst
        # defining dummy data which will be registered
        contract_id = 'cdb_' + str(contract_id_num) + '_contract'  # if consent_id_num is 1 then consent_id = c_001
        data = {
            "access_token": "a_t",
            "contract_id": contract_id
        }

        headers = requests.utils.default_headers()
        user_agent = 'UserAgent' + str(contract_id_num)
        headers.update(
            {
                'User-Agent': user_agent,
                'Connection': 'Keep-Alive',
            }
        )
        try:
            r = requests.post(url='http://localhost:5001/contract_trace', json=data, headers=headers)
            response_data = r.json()
            response_data_trace_contract_lst.append(response_data)
        except Exception as ex:
            print(ex)

    # call test register data sequentially to test its API's performance
    def run_test_register_data(self, lst_consent_num):
        global response_uri_lst
        st = time.time()
        for item in lst_consent_num:
            self.test_register_data_api(item)
        et = time.time()
        print("\n Time taken to register all data is {:.2f} seconds".format(round((et - st), 3)))
        # print(response_uri_lst)

    # call test register data parallely to test its API's performance
    def run_parallel_test_register_data(self, n_thread):
        try:
            global response_uri_lst
            args_set = [(0,), (1,), ]
            st = time.time()
            threads = [threading.Thread(target=obj.test_register_data_api, args=args_set[i]) for i in range(n_thread)]
            [t.start() for t in threads]
            [t.join() for t in threads]
            et = time.time()
            print("\n Time taken to register all data is {:.2f} seconds".format(round((et - st), 3)))
            # print(response_uri_lst)
        except Exception as ex:
            print(ex)

    # call test initiate data transfer sequentially to test its API's performance
    def run_test_init_data_transfer(self):
        global response_uri_lst
        st = time.time()
        self.test_init_data_transfer_api()
        et = time.time()
        print("\n Time taken to perform all init data transfer is {:.2f} seconds".format(round((et - st), 3)))
        # print(response_data_transfer_lst)

    # call test confirm data receipt sequentially to test its API's performance
    def run_test_confirm_data_receipt(self):
        hash_ctr = 0
        local_response_data_transfer_lst = []
        # start of changes by Uttam on 16 Sep to transact with DB
        if flag_transact_with_db:
            obj = transact_with_db()
            response_data_transfer_df = obj.fetch_records_in_df('transferred_data')
            response_data_transfer_df = response_data_transfer_df.loc[
                response_data_transfer_df['signature_of_receiver'] == '']
        else:
            # end of changes by Uttam on 16 Sep to transact with DB
            response_data_transfer_df = pd.read_csv("../src/utils/transferred_data.csv")
        for idx, row in response_data_transfer_df.iterrows():
            temp_dict = {}
            temp_dict['sender_id'] = row['sender_id']
            temp_dict['signature_of_sender'] = row['signature_of_sender']
            temp_dict['uri'] = row['uniform_resource_identifier']
            temp_dict['hash'] = 'cdb_' + str(hash_ctr) + '_hash'
            hash_ctr += 1
            local_response_data_transfer_lst.append(temp_dict)
        st = time.time()
        self.test_confirm_data_receipt_api(local_response_data_transfer_lst)
        et = time.time()
        print("\n Time taken to perform all confirm data receipt is {:.2f} seconds".format(round((et - st), 3)))
        # print(response_confirm_data_receipt_lst)

    # call test get data trace based on consent id sequentially to test its API's performance
    def run_test_get_data_trace_consent(self, lst_consent_ids):
        st = time.time()
        for item in lst_consent_ids:
            self.test_get_data_trace_consent_api(item)
        et = time.time()
        print("\n \n Time taken to fetch all data trace based on consent ids is {:.2f} seconds".format(
            round((et - st), 3)))
        # print(response_data_trace_consent_lst)

    # call test get data trace based on contract id sequentially to test its API's performance
    def run_test_get_data_trace_contract(self, lst_contract_ids):
        st = time.time()
        for item in lst_contract_ids:
            self.test_get_data_trace_contract_api(item)
        et = time.time()
        print("\n \n Time taken to fetch all data trace based on contract ids is {:.2f} seconds".format(
            round((et - st), 3)))
        # print(response_data_trace_contract_lst)


if __name__ == "__main__":

    smashhit_name = 'VW_Receiver'  # Traceability App  # can be passed as args using args parser when run from commandline
    num_requests = 100  # can be passed as args using args parser when run from commandline
    response_uri_lst, response_data_transfer_lst, response_confirm_data_receipt_lst, response_data_trace_consent_lst, response_data_trace_contract_lst = [], [], [], [], []
    obj = test_functionalities()

    if smashhit_name == 'Steve_Sender':
        ## testing response time for registering data without any multithreading or multiprocessing
        lst_consent_num = [i for i in range(num_requests)]
        obj.run_test_register_data(lst_consent_num)

        ## testing response time for registering data with multithreading
        # num_threads = 2
        # obj.run_parallel_test_register_data(num_threads)

        ## testing response time for init  data transfer without any multithreading or multiprocessing
        obj.run_test_init_data_transfer()

        # main.py of the module needs to run here with smashhit_name as receiver if data not passed with correct reference
        # os.system("python ../src/traceability_module/main.py --name='receiver'")  # or manually

        # running get data trace based on consent_id
        lst_dummy_consent_num = [i for i in range(num_requests)]
        obj.run_test_get_data_trace_consent(lst_dummy_consent_num)

        # running get data trace based on contract_id
        lst_dummy_contract_num = [i for i in range(num_requests)]
        obj.run_test_get_data_trace_contract(lst_dummy_contract_num)
    elif smashhit_name == 'VW_Receiver':
        ## testing response time for confirm data receipt without any multithreading or multiprocessing
        obj.run_test_confirm_data_receipt()

        # running get data trace based on consent_id
        lst_dummy_consent_num = [i for i in range(num_requests)]
        obj.run_test_get_data_trace_consent(lst_dummy_consent_num)

        # running get data trace based on contract_id
        lst_dummy_contract_num = [i for i in range(num_requests)]
        obj.run_test_get_data_trace_contract(lst_dummy_contract_num)
