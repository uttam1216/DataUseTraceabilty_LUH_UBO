from src.utils.digital_signature import DigitalSignature, _get_hash
from src.traceability_manager.data_processing_logs import DataProcessingLogs, _get_data_id, onboard as logs_onboard
import pandas as pd
from src.utils import encryption_module as em
from src.utils.util import transact_with_db, flag_transact_with_db
import binascii


# function to verify the signature
def _verify_signature(smashhit_id, signed_data, signature,
                      path_to_records_table='../../src/utils/records_table.csv'):
    # verify that the signature of the smashHit id belongs to the data
    # lookup public key of smashhit_id then use public key to check signature

    try:
        # start of changes by Uttam on 16 Sep to transact with DB
        if flag_transact_with_db:
            obj = transact_with_db()
            records_df = obj.fetch_records_in_df('records')
        else:
            # end of changes by Uttam on 16 Sep to transact with DB
            records_df = pd.read_csv(path_to_records_table)
        indexes = records_df.index[records_df['uniform_resource_identifier'] == str(smashhit_id)]
        if len(indexes) == 0:
            raise ValueError(f'company id: {smashhit_id} seems to be not present in the list of actors')
        index = indexes[-1]
        path_to_public_key_smashhit = records_df.loc[index, 'path_to_public_key']
        public_key_smashhit = em.load_public_key(path_to_public_key_smashhit)
        signature = binascii.unhexlify(signature)
        try:
            public_key_smashhit.verify(signature=signature, data=signed_data)
            # this signature is actually the signed_hash done by module, here the manager verifies the signed data
        except Exception as ex:
            print(ex)
            raise ValueError('Invalid signature: Verify that signature and hash are correct')
        return ""
    except ValueError as e:
        return e.args[0]


def onboard(actor):
    response = logs_onboard(actor)
    return response


class TraceabilityManager:
    def __init__(self, log_path_registered_data, log_path_transferred_data, path_to_private_key, path_to_public_key):
        # read public key
        self.public_key = em.load_public_key(path_to_public_key)
        # public_key = em.load_public_key(path_to_public_key)
        # read private key (using passphrase)
        self.private_key = em.load_private_key(path_to_private_key)
        # private_key = em.load_private_key(path_to_private_key)

        self.own_signature = DigitalSignature(private_key=self.private_key, public_key=self.public_key)

        self.logs = DataProcessingLogs(log_path_registered_data=log_path_registered_data,
                                       log_path_transferred_data=log_path_transferred_data)

    # function to register data by calling data processing logs and verify sender's signature
    def register_data(self, smashhit_id, hash_data, signed_hash, consent_id, contract_id, fingerprint, origin,
                      creation_time, expiration_time):
        byted_hash = _get_hash(hash_data)
        verify = _verify_signature(smashhit_id=smashhit_id,
                                   signed_data=byted_hash,
                                   signature=signed_hash)
        # Data should not be registered if verification did not happen successfully
        if verify == "" or verify is None:
            uniform_resource_identifier = self.logs.register_data(smashhit_id=smashhit_id, hash_data=str(hash_data),
                                                                  signed_hash=signed_hash, consent_id=consent_id,
                                                                  contract_id=contract_id, fingerprint=fingerprint,
                                                                  origin=origin, creation_time=creation_time,
                                                                  expiration_time=expiration_time)
            central_signature = self.own_signature.sign_data(byted_hash)
            central_signature = binascii.hexlify(central_signature).decode('ascii')
        else:
            uniform_resource_identifier = ""
            central_signature = ""

        return central_signature, uniform_resource_identifier, verify

    # function to notify data transfer
    def notify_data_transfer(self, uniform_resource_identifier, sender_id, receiver_id, signature_of_sender):
        hash_data = _get_hash(str(uniform_resource_identifier) + str(sender_id) + str(receiver_id))
        # created new so that the hash and signature can be checked with public key of sender by manager
        verify = _verify_signature(smashhit_id=sender_id,
                                   signed_data=hash_data,
                                   signature=signature_of_sender
                                   )
        # if verification of the sender's signature was not a success then the data transfer should not happen
        if verify == "" or verify is None:
            log = self.logs.log_data_transfer(uniform_resource_identifier, sender_id, receiver_id,
                                              signature_of_sender=signature_of_sender)
        else:
            log = " Data transfer failed."
        m = verify + log
        return f"{verify}. {log}" if m != "" else m

    # function to verify data received by a company after the data transfer was done
    def verify_received_data(self, hash_data, uniform_resource_identifier, sender_id, receiver_id,
                             signature_of_sender, signature_of_receiver):
        try:
            # check sender signature
            hash_data_sender = _get_hash(str(uniform_resource_identifier) + str(sender_id) + str(receiver_id))
            verify_sender = _verify_signature(smashhit_id=sender_id,
                                              signed_data=hash_data_sender,
                                              signature=signature_of_sender
                                              )

            # check receiver signature
            hash_data = hash_data.decode('utf-8') if not isinstance(hash_data, str) else hash_data
            hash_data_receiver = _get_hash(str(uniform_resource_identifier) + str(sender_id) + str(receiver_id) +
                                           str(signature_of_sender) + str(hash_data))
            verify_receiver = _verify_signature(smashhit_id=receiver_id,
                                                signed_data=hash_data_receiver,
                                                signature=signature_of_receiver
                                                )

            # lookup in logs if hash belongs to the uniform_resource_identifier we look into the registered data if
            # for the given identifier, there is at least one signed_hash (signature) corresponding to the hash_data
            # (original/native data)

            data_id = _get_data_id(hash_data)
            if data_id != str(uniform_resource_identifier):
                raise ValueError(
                    f'Mismatch between the hash {hash_data} and data identifier (uri) {uniform_resource_identifier}. ')

            # log receiving of data
            log = self.logs.log_data_transfer(uniform_resource_identifier, sender_id, receiver_id,
                                              signature_of_sender=signature_of_sender,
                                              signature_of_receiver=signature_of_receiver)

            # reaching this point means that there is no mismatch between hash_data and data_id
            m = verify_sender + verify_receiver + log
            return f"{verify_sender}. {verify_receiver}. {log}" if m != "" else m
        except ValueError as e:
            return e.args[0]

    # function to call the function present inside data processing logs to fetch data trace based on consent id
    def get_consent_data_trace(self, consent_id):
        # add in the documentation for smashHit platform that we assume that the check who can get which traces
        # is NOT done here
        return self.logs.get_consent_data_trace(consent_id)

    def check_actor_name(self, actor_name):
        # add in the documentation for smashHit platform that we assume that the check who can get which traces
        # is NOT done here
        return self.logs.check_actor_name(actor_name)

    # function to call the function present inside data processing logs to fetch data trace based on contract id
    def get_contract_data_trace(self, contract_id):
        # add in the documentation for smashHit platform that we assume that the check who can get which traces
        # is NOT done here
        return self.logs.get_contract_data_trace(contract_id)
