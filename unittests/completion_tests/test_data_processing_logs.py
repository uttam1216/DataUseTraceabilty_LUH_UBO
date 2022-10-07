import datetime
import hashlib
import os
from unittest import TestCase
import uuid
import binascii

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from src.traceability_manager.data_processing_logs import DataProcessingLogs


class TestDataProcessingLogs(TestCase):
    def setUp(self) -> None:
        # this method will be executed before EACH test method
        root = 'src'
        prefix = ''
        while not os.path.exists(f'{prefix}{root}'):
            prefix = f'../{prefix}'
        self.log_path_registered_data = f'{prefix}src/utils/registered_data.csv'
        self.log_path_transferred_data = f'{prefix}src/utils/transferred_data.csv'
        self.data_processing_logs = DataProcessingLogs(self.log_path_registered_data, self.log_path_transferred_data)

        self.data = b'form the data to the signed hash'
        self.hash_data = hashlib.sha256()
        self.hash_data.update(self.data)
        self.hash_data = self.hash_data.digest()

        # generation of private and public keys

        self.path_to_private_key = f'{prefix}src/keys/id_0_ed25519'
        self.path_to_public_key = f'{prefix}src/keys/id_0_ed25519.pub'
        self.path_to_private_key_sender = f'{prefix}src/keys/id_1_ed25519'
        self.path_to_public_key_sender = f'{prefix}src/keys/id_1_ed25519.pub'
        self.path_to_private_key_receiver = f'{prefix}src/keys/id_2_ed25519'
        self.path_to_public_key_receiver = f'{prefix}src/keys/id_2_ed25519.pub'

        def get_pemlines(pemlines_path):
            with open(pemlines_path, 'rb') as pem_in:
                pemlines = pem_in.read()
            return pemlines

        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(get_pemlines(self.path_to_private_key))
        self.public_key = ed25519.Ed25519PublicKey.from_public_bytes(get_pemlines(self.path_to_private_key))
        self.private_key_sender = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.path_to_private_key_sender))
        self.public_key_sender = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.path_to_private_key_sender))

        self.private_key_receiver = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.path_to_private_key_receiver))
        self.public_key_receiver = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.path_to_private_key_receiver))

        self.signed_hash = self.private_key.sign(self.hash_data)
        self.consent_id = uuid.uuid1()
        self.contract_id = str(self.consent_id) + '_contract'
        self.origin = uuid.uuid1()
        self.smashhit_id = uuid.uuid1()

        date_time_obj = datetime.datetime.strptime('2022-06-10 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.creation_time = date_time_obj.time()
        date_time_obj = datetime.datetime.strptime('2022-06-29 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.expiration_time = date_time_obj.time()
        self.uniform_resource_identifier = uuid.uuid1()
        self.sender_id = self.origin
        self.receiver_id = uuid.uuid1()
        self.signature_of_sender = self.private_key_sender.sign(self.data)
        self.signature_of_sender = binascii.hexlify(self.signature_of_sender).decode('ascii')
        self.signature_of_receiver = self.private_key_receiver.sign(self.data)
        self.signature_of_receiver = binascii.hexlify(self.signature_of_receiver).decode('ascii')

    def test_register_data(self):
        try:
            self.data_processing_logs.register_data(smashhit_id=self.smashhit_id,
                                                    hash_data=self.hash_data,
                                                    signed_hash=self.signed_hash,
                                                    consent_id=self.consent_id,
                                                    contract_id=self.contract_id,
                                                    origin=self.origin,
                                                    creation_time=self.creation_time,
                                                    expiration_time=self.expiration_time)
        except ValueError as e:
            print(e)
        except Exception as e:
            self.fail(f'Exception raised\n{e}')

    def test_get_data_trace(self):
        try:
            self.data_processing_logs.get_consent_data_trace(self.consent_id)
        except ValueError as e:
            print(e)
        except:
            self.fail('Exception raised')

    def test_log_data_transfer(self):
        try:
            self.data_processing_logs.log_data_transfer(self.uniform_resource_identifier, self.sender_id,
                                                        self.receiver_id, self.signature_of_sender,
                                                        self.signature_of_receiver)
        except ValueError as e:
            print(e)
        except Exception as e:
            self.fail(f'Exception raised\n{e}')

