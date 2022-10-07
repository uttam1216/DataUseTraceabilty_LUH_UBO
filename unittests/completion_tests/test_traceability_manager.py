import datetime
import hashlib
import os
from unittest import TestCase
from cryptography.exceptions import InvalidSignature
from src.utils import encryption_module as em
import uuid
import pandas as pd
from cryptography.hazmat.primitives.asymmetric import ed25519
import binascii

from src.traceability_manager.traceability_manager import TraceabilityManager, _verify_signature


class TestTraceabilityManager(TestCase):
    def setUp(self) -> None:
        root = 'src'
        prefix = ''
        while not os.path.exists(f'{prefix}{root}'):
            prefix = f'../{prefix}'

        path_to_private_keys = f'{prefix}src/keys'
        path_to_public_keys = f'{prefix}src/keys'

        # we insert smashhit data into the records
        path_to_records_table = f"{prefix}src/utils/records_table.csv"
        table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
        if os.path.exists(path_to_records_table):
            os.remove(path_to_records_table)
        records_df = pd.DataFrame(columns=table_columns)

        actors = ['sender', 'receiver', 'manager', 'own_smashhit']
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
            records_df = records_df.append(new_record, ignore_index=True)
            records_df = pd.DataFrame(records_df, columns=table_columns)

        records_df.to_csv(path_to_records_table)

        self.path_to_private_key = f'{prefix}src/keys/id_0_ed25519'
        self.path_to_public_key = f'{prefix}src/keys/id_0_ed25519.pub'
        self.path_to_private_key_sender = records_df.loc[0, 'path_to_private_key']  # 0 = position of sender
        self.path_to_public_key_sender = records_df.loc[0, 'path_to_public_key']
        self.path_to_private_key_receiver = records_df.loc[1, 'path_to_private_key']
        self.path_to_public_key_receiver = records_df.loc[1, 'path_to_public_key']
        self.own_smashhit_id = records_df.loc[3, 'uniform_resource_identifier']
        self.log_path_registered_data = f'{prefix}src/utils/registered_data.csv'
        self.log_path_transferred_data = f'{prefix}src/utils/transferred_data.csv'
        self.traceability_manager = TraceabilityManager(log_path_registered_data=self.log_path_registered_data,
                                                        log_path_transferred_data=self.log_path_transferred_data,
                                                        path_to_private_key=self.path_to_private_key,
                                                        path_to_public_key=self.path_to_public_key)

        def get_pemlines(pemlines_path):
            with open(pemlines_path, 'rb') as pem_in:
                pemlines = pem_in.read()
            return pemlines

        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(get_pemlines(self.path_to_private_key))
        self.public_key = ed25519.Ed25519PublicKey.from_public_bytes(get_pemlines(self.path_to_private_key))

        self.data = b'here is the data'
        hash_data = hashlib.sha256()
        hash_data.update(self.data)
        self.hash_data = hash_data.digest()
        self.signed_hash = self.private_key.sign(self.hash_data)
        self.signed_hash = binascii.hexlify(self.signed_hash).decode('ascii')
        self.uniform_resource_identifier = uuid.uuid1()
        self.consent_id = uuid.uuid1()
        self.contract_id = str(self.consent_id) + '_contract'
        self.origin = uuid.uuid1()
        self.sender_id = uuid.uuid1()
        self.receiver_id = uuid.uuid1()
        self.signature = self.private_key.sign(self.data)
        self.signature = binascii.hexlify(self.signature).decode('ascii')

        self.private_key_sender = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.path_to_private_key_sender))
        self.public_key_sender = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.path_to_private_key_sender))
        self.signature_of_sender = self.private_key_sender.sign(self.data)
        self.signature_of_sender = binascii.hexlify(self.signature_of_sender).decode('ascii')

        self.private_key_receiver = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.path_to_private_key_receiver))
        self.public_key_receiver = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.path_to_private_key_sender))
        self.signature_of_receiver = self.private_key_receiver.sign(self.data)
        self.signature_of_receiver = binascii.hexlify(self.signature_of_receiver).decode('ascii')

        date_time_obj = datetime.datetime.strptime('2022-06-10 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.creation_time = date_time_obj.time()
        date_time_obj = datetime.datetime.strptime('2022-06-29 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.expiration_time = date_time_obj.time()

    def test_register_data(self):
        try:
            self.traceability_manager.register_data(smashhit_id=self.own_smashhit_id,
                                                    hash_data=self.hash_data,
                                                    signed_hash=self.signed_hash,
                                                    consent_id=self.consent_id,
                                                    contract_id=self.contract_id,
                                                    origin=self.origin,
                                                    expiration_time=self.expiration_time,
                                                    creation_time=self.creation_time)

        except ValueError as e:
            print(e)
        except InvalidSignature as e:
            print(e)
        except:
            self.fail('Exception raised')

    def test_notify_data_transfer(self):
        try:
            self.traceability_manager.notify_data_transfer(uniform_resource_identifier=self.uniform_resource_identifier,
                                                           sender_id=self.sender_id,
                                                           receiver_id=self.receiver_id,
                                                           signature_of_sender=self.signature_of_sender)
        except ValueError as e:
            print(e)
        except InvalidSignature as e:
            print(e)
        except:
            self.fail('Exception raised')

    def test__verify_signature(self):
        try:
            _verify_signature(smashhit_id=self.own_smashhit_id,
                              signed_data=self.signed_hash,
                              signature=self.signature)
        except ValueError as e:
            print(e)
        except InvalidSignature as e:
            print(e)
        except:
            self.fail('Exception raised')

    def test_verify_received_data(self):
        try:
            self.traceability_manager.verify_received_data(hash_data=self.hash_data,
                                                           uniform_resource_identifier=self.uniform_resource_identifier,
                                                           sender_id=self.sender_id,
                                                           receiver_id=self.receiver_id,
                                                           signature_of_sender=self.signature_of_sender,
                                                           signature_of_receiver=self.signature_of_receiver)
        except ValueError as e:
            print(e)
        except InvalidSignature as e:
            print(e)
        except:
            self.fail('Exception raised')

    def test_get_data_trace(self):
        try:
            self.traceability_manager.get_consent_data_trace(self.consent_id)
        except ValueError as e:
            print(e)
        except:
            self.fail('Exception raised')
