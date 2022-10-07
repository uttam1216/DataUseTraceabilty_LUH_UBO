import datetime
import os
import binascii
import uuid
from unittest import TestCase

import pandas as pd
from cryptography.hazmat.primitives.asymmetric import ed25519

from src.traceability_manager.traceability_manager import TraceabilityManager, _verify_signature
from src.utils.digital_signature import _get_hash
from src.utils.util import debug, get_record, log_path_registered_data, log_path_transferred_data, \
    registered_data_columns, transferred_data_columns
from src.utils import clean_keys, remove_csv_files


class TestTraceabilityManager(TestCase):
    def setUp(self) -> None:
        if not debug:
            clean_keys()
            remove_csv_files()
        path_to_records_table = "../../src/utils/records_table.csv"
        if os.path.exists(path_to_records_table):
            os.remove(path_to_records_table)

        def get_pemlines(pemlines_path):
            with open(pemlines_path, 'rb') as pem_in:
                pemlines = pem_in.read()
            return pemlines

        # we insert smashhit data into the records
        self.sender = get_record("sender")
        self.receiver = get_record("receiver")
        self.manager = get_record("manager")
        self.provider = get_record("provider")

        self.private_key_sender = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.sender["path_to_private_key"]))
        self.public_key_sender = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.sender["path_to_public_key"]))

        self.private_key_receiver = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.receiver["path_to_private_key"]))
        self.public_key_receiver = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.receiver["path_to_public_key"]))

        self.private_key_manager = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.manager["path_to_private_key"]))
        self.public_key_manager = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.manager["path_to_public_key"]))

        self.private_key_provider = ed25519.Ed25519PrivateKey.from_private_bytes(
            get_pemlines(self.provider["path_to_private_key"]))
        self.public_key_provider = ed25519.Ed25519PublicKey.from_public_bytes(
            get_pemlines(self.provider["path_to_public_key"]))

        path_to_private_key_manager = self.manager["path_to_private_key"]
        path_to_public_key_manager = self.manager["path_to_public_key"]
        self.traceability_manager = TraceabilityManager(log_path_registered_data=log_path_registered_data,
                                                        log_path_transferred_data=log_path_transferred_data,
                                                        path_to_private_key=path_to_private_key_manager,
                                                        path_to_public_key=path_to_public_key_manager)

        data = "testing data"
        self.hash_data = _get_hash(data)
        self.data_id = uuid.uuid1()  # very important ("uniform_resource_identifier")
        self.consent_id = "c_002"
        self.contract_id = self.consent_id + '_contract'
        self.origin = "owner_uri"
        date_time_obj = datetime.datetime.strptime('2022-06-10 08:15:27.243860', '%Y-%m-%d %H:%M:%S.%f')
        self.creation_time = date_time_obj.time()
        self.expiration_time = '2022-06-29'

    def test_register_data(self):
        provider_id = self.provider["uniform_resource_identifier"]
        signed_hash = self.private_key_provider.sign(self.hash_data)
        signed_hash = binascii.hexlify(signed_hash).decode('ascii')
        central_signature, uniform_resource_identifier, _ = self.traceability_manager.register_data(
            smashhit_id=provider_id,
            hash_data=self.hash_data,
            signed_hash=signed_hash,
            consent_id=self.consent_id,
            contract_id=self.contract_id,
            origin=self.origin,
            expiration_time=self.expiration_time,
            creation_time=self.creation_time
        )

        df = pd.read_csv(log_path_registered_data)
        index = len(df) - 1
        new_central_signature = self.private_key_manager.sign(self.hash_data)
        new_central_signature = binascii.hexlify(new_central_signature).decode('ascii')
        new_uniform_resource_identifier = df.loc[index, 'uniform_resource_identifier']

        self.assertTrue((central_signature == new_central_signature) &
                        (str(uniform_resource_identifier) == new_uniform_resource_identifier))

    def test_notify_data_transfer(self):
        # the data needs to be registered to be transferred
        provider_id = self.provider["uniform_resource_identifier"]
        signed_hash = self.private_key_sender.sign(self.hash_data)
        signed_hash = binascii.hexlify(signed_hash).decode('ascii')
        registered_data_df = pd.DataFrame(columns=registered_data_columns)
        new_data = {'smashhit_id': provider_id, 'uniform_resource_identifier': self.data_id,
                    'hash_data': self.hash_data, 'signed_hash': signed_hash, 'consent_id': self.consent_id,
                    'origin': self.origin,
                    'creation_time': self.creation_time, 'expiration_time': self.expiration_time}
        registered_data_df = registered_data_df.append(new_data, ignore_index=True)
        registered_data_df.to_csv(log_path_registered_data, index=False)

        sender_id = self.sender["uniform_resource_identifier"]
        receiver_id = self.receiver["uniform_resource_identifier"]

        data_sender = _get_hash(str(self.data_id) + str(sender_id) + str(receiver_id))
        signature_of_sender = self.private_key_sender.sign(data_sender)
        signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')
        self.traceability_manager.notify_data_transfer(uniform_resource_identifier=self.data_id,
                                                       sender_id=sender_id,
                                                       receiver_id=receiver_id,
                                                       signature_of_sender=signature_of_sender)

        df = pd.read_csv(log_path_transferred_data)
        index = len(df) - 1
        self.assertTrue(((df.loc[index, 'uniform_resource_identifier'] == str(self.data_id)) &
                         (df.loc[index, 'sender_id'] == str(sender_id)) &
                         (df.loc[index, 'receiver_id'] == str(receiver_id)) &
                         (df.loc[index, 'signature_of_sender'] == signature_of_sender)))

    def test__verify_signature(self):
        signature = self.private_key_sender.sign(self.hash_data)
        signature = binascii.hexlify(signature).decode('ascii')
        sender_id = self.sender["uniform_resource_identifier"]
        self.assertTrue("" == _verify_signature(smashhit_id=sender_id,
                                                signed_data=self.hash_data,
                                                signature=signature))

    def test_verify_received_data(self):
        # the data need to be registered to be transferred
        provider_id = self.provider["uniform_resource_identifier"]
        signed_hash = self.private_key_sender.sign(self.hash_data)
        registered_data_df = pd.DataFrame(columns=registered_data_columns)
        new_data = {'smashhit_id': provider_id, 'uniform_resource_identifier': self.data_id,
                    'hash_data': self.hash_data, 'signed_hash': signed_hash, 'consent_id': self.consent_id,
                    'contract_id': self.contract_id, 'origin': self.origin,
                    'creation_time': self.creation_time, 'expiration_time': self.expiration_time}
        registered_data_df = registered_data_df.append(new_data, ignore_index=True)
        registered_data_df.to_csv(log_path_registered_data, index=False)

        sender_id = self.sender["uniform_resource_identifier"]
        receiver_id = self.receiver["uniform_resource_identifier"]
        data_sender = _get_hash(str(self.data_id) + str(sender_id) + str(receiver_id))
        signature_of_sender = self.private_key_sender.sign(data_sender)
        signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')

        transferred_data_df = pd.DataFrame(columns=transferred_data_columns)
        new_transfer = {'uniform_resource_identifier': str(self.data_id),
                        'sender_id': str(sender_id), 'receiver_id': str(receiver_id),
                        'signature_of_sender': str(signature_of_sender),
                        'signature_of_receiver': "", 'transfer_date_time': datetime.datetime.now(),
                        'confirm_date_time': ''}
        transferred_data_df = transferred_data_df.append(new_transfer, ignore_index=True)
        transferred_data_df.to_csv(log_path_transferred_data, index=False)

        data_receiver = _get_hash(str(self.data_id) + str(sender_id) + str(receiver_id) + str(signature_of_sender) +
                                  str(self.hash_data))
        signature_of_receiver = self.private_key_receiver.sign(data_receiver)
        signature_of_receiver = binascii.hexlify(signature_of_receiver).decode('ascii')
        self.assertTrue("" == self.traceability_manager.verify_received_data(hash_data=self.hash_data,
                                                                             uniform_resource_identifier=self.data_id,
                                                                             sender_id=sender_id,
                                                                             receiver_id=receiver_id,
                                                                             signature_of_sender=signature_of_sender,
                                                                             signature_of_receiver=signature_of_receiver))

    def test_get_data_trace(self):
        # the data need to be registered to be transferred
        provider_id = self.provider["uniform_resource_identifier"]
        signed_hash = self.private_key_sender.sign(self.hash_data)
        signed_hash = binascii.hexlify(signed_hash).decode('ascii')
        registered_data_df = pd.DataFrame(columns=registered_data_columns)
        new_data = {'smashhit_id': provider_id, 'uniform_resource_identifier': self.data_id,
                    'hash_data': self.hash_data, 'signed_hash': signed_hash, 'consent_id': self.consent_id,
                    'contract_id': self.contract_id, 'origin': self.origin,
                    'creation_time': self.creation_time, 'expiration_time': self.expiration_time}
        registered_data_df = registered_data_df.append(new_data, ignore_index=True)
        registered_data_df.to_csv(log_path_registered_data, index=False)

        sender_id = self.sender["uniform_resource_identifier"]
        receiver_id = self.receiver["uniform_resource_identifier"]
        data_sender = _get_hash(str(self.data_id) + str(sender_id) + str(receiver_id))
        signature_of_sender = self.private_key_sender.sign(data_sender)
        signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')
        data_receiver = _get_hash(str(self.data_id) + str(sender_id) + str(receiver_id) + str(signature_of_sender) +
                                  str(self.hash_data))
        signature_of_receiver = self.private_key_receiver.sign(data_receiver)
        signature_of_receiver = binascii.hexlify(signature_of_receiver).decode('ascii')
        transferred_data_df = pd.DataFrame(columns=transferred_data_columns)
        new_transfer = {'uniform_resource_identifier': str(self.data_id),
                        'sender_id': str(sender_id), 'receiver_id': str(receiver_id),
                        'signature_of_sender': str(signature_of_sender),
                        'signature_of_receiver': str(signature_of_receiver)}
        transferred_data_df = transferred_data_df.append(new_transfer, ignore_index=True)
        transferred_data_df.to_csv(log_path_transferred_data, index=False)

        generated_trace_df = pd.DataFrame(transferred_data_df.iloc[[len(transferred_data_df) - 1]],
                                          columns=transferred_data_columns)
        generated_trace_df = generated_trace_df
        data_trace_df = self.traceability_manager.get_consent_data_trace(self.consent_id)
        if 'contract_id' in transferred_data_columns:
            self.assertTrue((len(generated_trace_df.to_dict()) == len(data_trace_df)))
        # self.assertTrue(generated_trace_df.equals(data_trace_df[transferred_data_columns]))
