import datetime
import hashlib
from unittest import TestCase
import uuid
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from src.traceability_module.traceability_module import TraceabilityModule
import os
import binascii

from src.utils.digital_signature import _get_hash


class TestTraceabilityModule(TestCase):

    def setUp(self) -> None:
        # this method will be executed before EACH test method
        root = 'src'
        prefix = ''
        while not os.path.exists(f'{prefix}{root}'):
            prefix = f'../{prefix}'

        self.own_smashhit_id = uuid.uuid1()
        self.url_to_manager = uuid.uuid1()
        self.data = b'here is the data'
        hash_data = hashlib.sha256()
        hash_data.update(self.data)
        self.hash_data = hash_data.digest()
        self.uniform_resource_identifier = uuid.uuid1()
        self.consent_id = uuid.uuid1()
        self.contract_id = str(self.consent_id) + '_contract'
        self.origin = uuid.uuid1()
        self.sender_id = uuid.uuid1()
        self.receiver_id = uuid.uuid1()
        self.path_to_private_key = f'{prefix}src/keys/id_0_ed25519'
        self.path_to_public_key = f'{prefix}src/keys/id_0_ed25519.pub'
        self.path_to_private_key_sender = f'{prefix}src/keys/id_1_ed25519'
        self.path_to_public_key_sender = f'{prefix}src/keys/id_1_ed25519.pub'

        self.traceability_module = TraceabilityModule(own_smashhit_id=self.own_smashhit_id,
                                                      path_to_private_key=self.path_to_private_key,
                                                      path_to_public_key=self.path_to_public_key,
                                                      url_to_manager=self.url_to_manager)

        def get_pemlines(pemlines_path):
            with open(pemlines_path, 'rb') as pem_in:
                pemlines = pem_in.read()
            return pemlines

        self.private_key_sender = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.path_to_private_key_sender))
        self.public_key_sender = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.path_to_private_key_sender))

        self.signature_of_sender = self.private_key_sender.sign(self.data)
        self.signature_of_sender = binascii.hexlify(self.signature_of_sender).decode('ascii')

        date_time_obj = datetime.datetime.strptime('2022-06-10 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.creation_time = date_time_obj.time()
        date_time_obj = datetime.datetime.strptime('2022-06-29 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.expiration_time = date_time_obj.time()

    def test_register_data(self):
        try:
            self.traceability_module.register_data(consent_id=self.consent_id,
                                                   contract_id=self.contract_id,
                                                   hash_data=self.hash_data,
                                                   origin=self.origin,
                                                   creation_time=self.creation_time,
                                                   expiration_time=self.expiration_time)
        except NotImplementedError as e:
            print(e)
        except ValueError as e:
            print(e)
        except InvalidSignature as e:
            print(e)
        except:
            self.fail('Exception raised')

    def test_notify_data_transfer(self):
        try:
            self.traceability_module.notify_data_transfer(uniform_resource_identifier=self.uniform_resource_identifier,
                                                          receiver_id=self.receiver_id)
        except NotImplementedError as e:
            print(e)
        except ValueError as e:
            print(e)
        except InvalidSignature as e:
            print(e)
        except:
            self.fail('Exception raised')

    def test_verify_received_data(self):
        try:
            self.traceability_module.verify_received_data(hash_data=self.hash_data,
                                                          uniform_resource_identifier=self.uniform_resource_identifier,
                                                          sender_id=self.sender_id,
                                                          signature_of_sender=self.signature_of_sender)
        except NotImplementedError as e:
            print(e)
        except ValueError as e:
            print(e)
        except InvalidSignature as e:
            print(e)
        except:
            self.fail('Exception raised')
