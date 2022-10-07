import datetime
import random
from unittest import TestCase
import uuid

import src.utils.util
from src.utils import encryption_module as em
import pandas as pd
from src.traceability_module.traceability_module import TraceabilityModule
import os
import binascii

from src.utils.digital_signature import _get_hash, DigitalSignature
from src.utils.util import registered_data_columns, transferred_data_columns, url_to_manager


class TestTraceabilityModule(TestCase):

    def setUp(self) -> None:
        # this method will be executed before EACH test method
        root = 'src'
        prefix = ''
        while not os.path.exists(f'{prefix}{root}'):
            prefix = f'../{prefix}'

        path_to_private_keys = f'{prefix}src/keys'
        path_to_public_keys = f'{prefix}src/keys'

        # we insert smashhit data into the records
        self.path_to_records_table = "../../src/utils/records_table.csv"
        self.table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
        if os.path.exists(self.path_to_records_table):
            self.records_df = pd.DataFrame(columns=self.table_columns)

            actors = ['sender', 'receiver', 'own_smashhit', 'manager', 'native']
            for present in self.records_df['actor'].to_list():
                actors.remove(present)

            # for each actor we assign a random uniform_resource_identifier, private key and public key
            for actor in actors:
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
                # insertion of the new record in table
                new_record = {'actor': actor, 'uniform_resource_identifier': uniform_resource_identifier,
                              'path_to_private_key': path_to_private_key, 'path_to_public_key': path_to_public_key}
                # ignore_index=True to avoid thinking about the index
                self.records_df = self.records_df.append(new_record, ignore_index=True)
                self.records_df = pd.DataFrame(self.records_df, columns=self.table_columns)
            self.records_df.to_csv(self.path_to_records_table, index=False)
        else:
            self.records_df = pd.read_csv(self.path_to_records_table)

        self.path_to_private_key_sender = self.records_df.loc[0, 'path_to_private_key']  # 0 = position of sender
        self.path_to_public_key_sender = self.records_df.loc[0, 'path_to_public_key']
        self.path_to_private_key_receiver = self.records_df.loc[1, 'path_to_private_key']
        self.path_to_public_key_receiver = self.records_df.loc[1, 'path_to_public_key']
        self.path_to_private_key_manager = self.records_df.loc[3, 'path_to_private_key']
        self.path_to_public_key_manager = self.records_df.loc[3, 'path_to_public_key']
        self.path_to_private_key_native = self.records_df.loc[4, 'path_to_private_key']
        self.path_to_public_key_native = self.records_df.loc[4, 'path_to_public_key']
        self.sender_id = self.records_df.loc[0, 'uniform_resource_identifier']
        self.receiver_id = self.records_df.loc[1, 'uniform_resource_identifier']
        self.manager_id = self.records_df.loc[3, 'uniform_resource_identifier']
        self.native_id = self.records_df.loc[4, 'uniform_resource_identifier']
        self.log_path_registered_data = f'{prefix}src/utils/registered_data.csv'
        self.log_path_transferred_data = f'{prefix}src/utils/transferred_data.csv'

        self.data = str.encode(f'this{random.randint(0, 15)}is{random.randint(0, 50)}the{random.randint(0, 1000)}data')
        self.hash_data = _get_hash(self.data)
        self.uniform_resource_identifier = self.native_id  # very important
        self.consent_id = uuid.uuid1()
        self.contract_id = str(self.consent_id) + '_contract'
        self.origin = uuid.uuid1()

        self.private_key_sender = em.load_private_key(self.path_to_private_key_sender)
        self.public_key_sender = em.load_public_key(self.path_to_public_key_sender)

        self.private_key_receiver = em.load_private_key(self.path_to_private_key_receiver)
        self.public_key_receiver = em.load_private_key(self.path_to_public_key_receiver)

        self.private_key_manager = em.load_private_key(self.path_to_private_key_manager)
        self.public_key_manager = em.load_public_key(self.path_to_public_key_manager)

        date_time_obj = datetime.datetime.strptime('2022-06-10 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.creation_time = date_time_obj.time()
        date_time_obj = datetime.datetime.strptime('2022-06-29 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.expiration_time = date_time_obj.time()

        self.log_path_registered_data = f'{prefix}src/utils/registered_data.csv'
        self.log_path_transferred_data = f'{prefix}src/utils/transferred_data.csv'

        self.path_to_consents = f'{prefix}src/utils/consents.csv'

    def test_register_data(self):
        self.traceability_module = TraceabilityModule(path_to_private_key=self.path_to_private_key_manager,
                                                      path_to_public_key=self.path_to_public_key_manager,
                                                      url_to_manager=url_to_manager,
                                                      own_smashhit_id=str(self.manager_id))
        digital_signature_manager = DigitalSignature(public_key=self.public_key_manager,
                                                     private_key=self.private_key_manager)
        signed_hash_manager = digital_signature_manager.sign_data(self.hash_data)
        signed_hash_manager = binascii.hexlify(signed_hash_manager).decode('ascii')
        result = self.traceability_module.register_data(
            consent_id=str(self.consent_id),
            contract_id=str(self.contract_id),
            hash_data=str(self.hash_data),
            origin=str(self.origin),
            creation_time=self.creation_time,
            expiration_time=self.expiration_time,
            path_to_records_table=self.path_to_records_table
        )

        central_signature, uniform_resource_identifier = result[0], result[1]

        df = pd.read_csv(self.log_path_registered_data)
        index = len(df) - 1
        new_uniform_resource_identifier = df.loc[index, 'uniform_resource_identifier']

        self.assertTrue((signed_hash_manager == central_signature) &
                        (str(uniform_resource_identifier) == new_uniform_resource_identifier))

    def test_notify_data_transfer(self):
        self.traceability_module = TraceabilityModule(own_smashhit_id=str(self.sender_id),
                                                      path_to_private_key=self.path_to_private_key_sender,
                                                      path_to_public_key=self.path_to_private_key_sender,
                                                      url_to_manager=url_to_manager)
        # we create a row in registered data containing the sender (first-hop company) hash_data
        hash_data = self.hash_data
        smashhit = src.utils.util.get_record('own_smashhit')
        path_to_private_key_smashhit = smashhit['path_to_private_key']
        path_to_public_key_smashhit = smashhit['path_to_public_key']
        private_key_smashhit = em.load_private_key(path_to_private_key_smashhit)
        public_key_smashhit = em.load_private_key(path_to_public_key_smashhit)

        signed_hash = private_key_smashhit.sign(hash_data)
        signed_hash = binascii.hexlify(signed_hash).decode('ascii')
        if os.path.exists(self.log_path_registered_data):
            registered_data_df = pd.read_csv(self.log_path_registered_data)
        else:
            registered_data_df = pd.DataFrame(columns=registered_data_columns)
        new_data = {'smashhit_id': str(self.sender_id),
                    'uniform_resource_identifier': str(self.uniform_resource_identifier),
                    'hash_data': str(hash_data),
                    'signed_hash': str(signed_hash), 'consent_id': str(self.consent_id),
                    'contract_id': str(self.contract_id), 'origin': str(self.origin),
                    'creation_time': str(self.creation_time),
                    'expiration_time': str(self.expiration_time)}
        registered_data_df = registered_data_df.append(new_data, ignore_index=True)
        registered_data_df.to_csv(self.log_path_registered_data, index=False)

        data_sender = str(self.uniform_resource_identifier) + str(self.sender_id) + str(self.receiver_id)
        hash_data_sender = _get_hash(data_sender)
        signature_of_sender = self.private_key_sender.sign(hash_data_sender)
        signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')

        var_msg = self.traceability_module.notify_data_transfer(
            uniform_resource_identifier=str(self.uniform_resource_identifier), receiver_id=str(self.receiver_id))


        df = pd.read_csv(self.log_path_transferred_data)

        index = len(df) - 1
        self.assertTrue(((df.loc[index, 'uniform_resource_identifier'] == str(self.uniform_resource_identifier))) &
                        (df.loc[index, 'sender_id'] == str(self.sender_id)) &
                        (df.loc[index, 'receiver_id'] == str(self.receiver_id)) &
                        (df.loc[index, 'signature_of_sender'] == str(signature_of_sender)))

    def test_verify_received_data(self):
        self.traceability_module = TraceabilityModule(own_smashhit_id=str(self.receiver_id),
                                                      path_to_private_key=self.path_to_private_key_receiver,
                                                      path_to_public_key=self.path_to_private_key_receiver,
                                                      url_to_manager=url_to_manager)
        # we create a row in registered data containing the sender (first-hop company) hash_data
        hash_data = self.hash_data
        signed_hash = self.private_key_sender.sign(hash_data)
        signed_hash = binascii.hexlify(signed_hash).decode('ascii')
        if os.path.exists(self.log_path_registered_data):
            registered_data_df = pd.read_csv(self.log_path_registered_data)
        else:
            registered_data_df = pd.DataFrame(columns=registered_data_columns)
        new_data = {'uniform_resource_identifier': self.uniform_resource_identifier, 'hash_data': hash_data,
                    'signed_hash': signed_hash, 'consent_id': self.consent_id, 'contract_id': self.contract_id,
                    'origin': self.origin, 'creation_time': self.creation_time, 'expiration_time': self.expiration_time}
        registered_data_df = registered_data_df.append(new_data, ignore_index=True)
        registered_data_df.to_csv(self.log_path_registered_data, index=False)

        data_sender = _get_hash(str(self.uniform_resource_identifier) + str(self.sender_id) + str(self.receiver_id))
        signature_of_sender = self.private_key_sender.sign(data_sender)
        signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')

        # we create a row in transferred data containing the transferred data
        data = {
            'uniform_resource_identifier': self.uniform_resource_identifier,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'signature_of_sender': signature_of_sender,
            'signature_of_receiver': '',
            'transfer_date_time': datetime.datetime.now(),
            'confirm_date_time': ''
        }
        if os.path.exists(self.log_path_transferred_data):
            transferred_data_df = pd.read_csv(self.log_path_transferred_data)
        else:
            transferred_data_df = pd.DataFrame(columns=transferred_data_columns)
        transferred_data_df = transferred_data_df.append(data, ignore_index=True)
        transferred_data_df.to_csv(self.log_path_transferred_data, index=False)

        self.assertTrue('' == self.traceability_module.verify_received_data(hash_data=str(hash_data),
                                                                            uniform_resource_identifier=str(
                                                                                self.uniform_resource_identifier),
                                                                            sender_id=str(self.sender_id),
                                                                            signature_of_sender=signature_of_sender))
