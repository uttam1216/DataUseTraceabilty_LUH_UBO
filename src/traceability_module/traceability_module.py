import os
import pandas as pd
from requests import post, get
import binascii
from src.traceability_manager import initialize_records
from src.traceability_manager.traceability_manager import TraceabilityManager
from src.utils import encryption_module as em
from src.utils.digital_signature import DigitalSignature, _get_hash
from src.utils.util_module import calls_ready, manager_name, url_to_manager, transact_with_db, flag_transact_with_db


# defining a class for the module with various functionalities
class TraceabilityModule:
    def __init__(self, path_to_private_key, path_to_public_key, url_to_manager, own_smashhit_id):
        public_key = em.load_public_key(path_to_public_key)
        private_key = em.load_private_key(path_to_private_key)

        self.own_smashhit_id = own_smashhit_id

        self.own_signature = DigitalSignature(private_key=private_key, public_key=public_key)

        self.manager_caller = TraceabilityManagerCaller(url=url_to_manager)

    # function to register the data by passing it to the manager
    def register_data(self, consent_id, contract_id, hash_data, fingerprint, access_token, origin=None,
                      creation_time=None,
                      expiration_time=None, path_to_records_table="../../src/utils/records_table.csv"):
        # already we are now getting a hash of the data so this step is no more required..commented on 23 Sep Uttam
        if isinstance(hash_data, str):
           byted_hash_data = _get_hash(hash_data)  # to convert str to bytes for signing
           # print(byted_hash_data)

        # we assume that the hash_data already contains everything necessary (data and eventually metadata)
        signed_hash = self.own_signature.sign_data(byted_hash_data)
        encoded_sign = binascii.hexlify(signed_hash).decode('ascii')
        result = self.manager_caller.register_data(
            smashhit_id=self.own_smashhit_id,
            hash_data=hash_data,
            signed_hash=encoded_sign,
            consent_id=consent_id,
            contract_id=contract_id,
            fingerprint=fingerprint,
            access_token=access_token,
            origin=origin,
            creation_time=creation_time,
            expiration_time=expiration_time
        )
        signed_hash_manager, uniform_resource_identifier = result[0], result[1]
        if result[2] != '':
            # there is a message that needs to be sent back, probably from manager api
            return result

        # check signature of manager
        # In the reality, the company does not access the database to get the public key of the manager but gets it
        # from any provider of public keys. The same holds for the public identifier of the receiver
        # start of changes by Uttam on 16 Sep to transact with DB
        if flag_transact_with_db:
            obj = transact_with_db()
            records_df = obj.fetch_records_in_df('records')
        else:
            # end of changes by Uttam on 16 Sep to transact with DB
            if not os.path.exists(path_to_records_table):
                raise ValueError(f'The path {path_to_records_table} is not correct')
            records_df = pd.read_csv(path_to_records_table)
        indexes = records_df.index[records_df['actor'] == manager_name]
        if len(indexes) == 0:
            raise ValueError('manager_id seems to be not present in the list of actors')
        if len(indexes) > 1:
            raise ValueError(f'{len(indexes)} different positions for smash_id, looks strange')
        index = indexes[0]
        path_to_public_key_manager = records_df.loc[index, 'path_to_public_key']
        public_key_manager = em.load_public_key(path_to_public_key_manager)
        signed_hash_manager = binascii.unhexlify(signed_hash_manager)
        try:
            public_key_manager.verify(signature=signed_hash_manager, data=byted_hash_data)
        except Exception as ex:
            result[2] = ex if isinstance(ex, str) else 'Failed to verify manager signature in traceability module'
        return result

    # function to notify that a company which registered the data, now wants to transfer the data
    def notify_data_transfer(self, uniform_resource_identifier, access_token, receiver_id):
        other_data = str(uniform_resource_identifier) + str(self.own_smashhit_id) + str(receiver_id)
        signed_data = self.own_signature.sign_data(data=_get_hash(other_data))
        signed_data = binascii.hexlify(signed_data).decode('ascii')

        # TODO @Stefan in the sequence diagram we have in addition a certificate, is that different from the signature?
        # steve: the presence or not of the certificate probably depends on the encryption technology used
        # I am also not too sure about that. So it contains the information about sender, receiver, data and a
        # signature so we know its valid and was not tempered with.

        # TODO asyncronous call?
        # We don't want to wait on the completion of the following statement

        result = self.manager_caller.notify_data_transfer(uniform_resource_identifier=uniform_resource_identifier,
                                                          access_token=access_token,
                                                          sender_id=self.own_smashhit_id,
                                                          receiver_id=receiver_id,
                                                          signature_of_sender=signed_data)

        # TODO explicitly send the data directly the receiver company.
        """ 
        It is done outside the smashhit platform since no clear data should flow inside smashhit. Since we do not
        pass through the manger for sending the data, it is important that the sender directly send to the receiver 
        (probably using smashhit)
            - hash of data with metadata sent
            - uniform resource identifier of the registered data
            - sender id
            - signature of sender
        for allowing the signature of the receiver and forward them afterwards to the manager.
        """

        return result, self.own_smashhit_id, signed_data

    # function to verify whether the data is received by the recipient
    def verify_received_data(self, hash_data, uniform_resource_identifier, sender_id,
                             signature_of_sender, access_token):
        # stores the received data for future use
        """
        Since data in clear (without hash) shouldn't be present on the smashhit platform, we assume that the company
        receives the data and metadata directly from the sender and stores it internally. the hash is sent to the
        receiver through the platform to allow smashhit to monitor the data flow.
        """

        # recompute the hash of data with metadata
        # self.own_smashhit_id value will be whatever is set as smashhit_name in the main.py of the module

        # add own signature
        hash_data = str(hash_data) if isinstance(hash_data, bytes) else hash_data
        receiver_data = str(uniform_resource_identifier) + str(sender_id) + str(self.own_smashhit_id) + str(
            signature_of_sender) + str(hash_data)
        signature_of_receiver = self.own_signature.sign_data(receiver_data)
        signature_of_receiver = binascii.hexlify(signature_of_receiver).decode('ascii')

        # call manager to check the block
        return self.manager_caller.verify_received_data(hash_data=hash_data,
                                                        uniform_resource_identifier=uniform_resource_identifier,
                                                        sender_id=sender_id,
                                                        receiver_id=self.own_smashhit_id,
                                                        signature_of_sender=signature_of_sender,
                                                        access_token=access_token,
                                                        signature_of_receiver=signature_of_receiver)

    # function to call the manager to get the trace of data based on consent id used during registration
    def get_consent_data_trace(self, consent_id, access_token):
        # add in the documentation for smashHit platform that we assume that the check who can get which traces
        # is NOT done here
        return self.manager_caller.get_consent_data_trace(consent_id, access_token)

    # function to call the manager to get the trace of data based on contract id used during registration
    def get_contract_data_trace(self, contract_id, access_token):
        # add in the documentation for smashHit platform that we assume that the check who can get which traces
        # is NOT done here
        return self.manager_caller.get_contract_data_trace(contract_id, access_token)


class TraceabilityManagerCaller:
    def __init__(self, url):
        """
        REST Wrapper around the calls
        """
        # TODO: remove '/' in the end of url if there is one, before assigning it to self.url
        self.url = url
        self.calls_ready = calls_ready

        """
        To avoid that the module creates an instance of the real manager in case the calls are not ready, we are going 
        to wrap a controller her. The controller is the only one knowing how to access all the keys, all the 
        companies identifiers, how to get any information stored by any actor in the platform (included platform 
        database)
        """
        if not self.calls_ready:
            # The API calls are not ready, or we do not want use them, so
            # we temporarily connect the traceability module directly to the traceability manager
            initialize_records()
            root = 'src'
            prefix = ''
            while not os.path.exists(f'{prefix}{root}'):
                prefix = f'../{prefix}'
            log_path_registered_data = f'{prefix}src/utils/registered_data.csv'
            log_path_transferred_data = f'{prefix}src/utils/transferred_data.csv'

            path_to_records_table = f'{prefix}src/utils/records_table.csv'
            # start of changes by Uttam on 16 Sep to transact with DB
            if flag_transact_with_db:
                obj = transact_with_db()
                records_df = obj.fetch_records_in_df('records')
            else:
                # end of changes by Uttam on 16 Sep to transact with DB
                records_df = pd.read_csv(path_to_records_table)
            indexes = records_df.index[records_df['actor'] == 'manager']
            if len(indexes) == 0:
                raise ValueError('manager not present in the list of actors')
            path_to_public_key_manager = records_df.loc[indexes[0], 'path_to_public_key']
            path_to_private_key_manager = records_df.loc[indexes[0], 'path_to_private_key']

            self.traceability_manager = TraceabilityManager(log_path_registered_data=log_path_registered_data,
                                                            log_path_transferred_data=log_path_transferred_data,
                                                            path_to_private_key=path_to_private_key_manager,
                                                            path_to_public_key=path_to_public_key_manager)

    # TODO: put the response in case of calls.ready = True in the same format as the response of calls.ready = False
    def register_data(self, smashhit_id, hash_data, signed_hash, consent_id, contract_id, fingerprint, access_token,
                      origin, creation_time, expiration_time):
        # implement REST call
        # converting everything to string before passing

        new_data = {
            'smashhit_id': str(smashhit_id),
            'hash': str(hash_data) if not isinstance(hash_data, str) else hash_data,
            'signed_hash': str(signed_hash) if not isinstance(signed_hash, str) else signed_hash,
            'consent_id': str(consent_id),
            'contract_id': str(contract_id),
            'fingerprint': str(fingerprint),
            'origin': str(origin),
            'creation_time': str(creation_time),
            'expiration_time': str(expiration_time)
        }

        if self.calls_ready:
            if self.url == 'https://smashhit.ari-mobility.eu/api/traceability':
                response = post(url=f'{self.url}/register', json=new_data,
                                headers={'x-auth-token': access_token}).json()
            else:
                response = post(url=f'{self.url}/register', json=new_data).json()
            # Conversion of json dict to list
            lst_response = [response["signed_hash"], response["uri"], response["ERROR"]]
            response = lst_response
            # End of conversion of json dict to list
        else:
            # access_token is not required to be passed below internally
            response = self.traceability_manager.register_data(smashhit_id, hash_data, signed_hash, consent_id,
                                                               contract_id, fingerprint, origin,
                                                               creation_time, expiration_time)
        return response

    # function to notify the data transfer
    def notify_data_transfer(self, uniform_resource_identifier, access_token, sender_id, receiver_id,
                             signature_of_sender):
        # implement REST call
        data = {
            'uri': uniform_resource_identifier,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'signature_of_sender': signature_of_sender
        }
        if self.calls_ready:
            if self.url == 'https://smashhit.ari-mobility.eu/api/traceability':
                result = post(url=f'{self.url}/init_transfer', json=data,
                              headers={'x-auth-token': access_token})
            else:
                result = post(url=f'{self.url}/init_transfer', json=data)
            message = result.json()["message"]
            response = "" if result.status_code != 500 else message
        else:
            # access_token is not required to be passed below internally
            response = self.traceability_manager.notify_data_transfer(uniform_resource_identifier, sender_id,
                                                                      receiver_id, signature_of_sender)
        return response

    # function to verify the received data
    def verify_received_data(self, hash_data, uniform_resource_identifier, sender_id, receiver_id,
                             signature_of_sender, access_token, signature_of_receiver=None):
        # implement REST call

        new_data = {
            'uri': uniform_resource_identifier,
            'hash': hash_data.decode("utf-8") if not isinstance(hash_data, str) else hash_data,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'signature_of_sender': signature_of_sender,
            'signature_of_receiver': signature_of_receiver
        }

        if self.calls_ready:
            if self.url == 'https://smashhit.ari-mobility.eu/api/traceability':
                result = post(url=f'{self.url}/confirm_transfer', json=new_data,
                              headers={'x-auth-token': access_token})
            else:
                result = post(url=f'{self.url}/confirm_transfer', json=new_data)
            message = result.json()["message"]
            response = "" if result.status_code != 500 else message
        else:
            # access_token is not required to be passed below internally
            response = self.traceability_manager.verify_received_data(hash_data, uniform_resource_identifier, sender_id,
                                                                      receiver_id, signature_of_sender,
                                                                      signature_of_receiver)

        return response

    # function to get trace of get trace of data using consent id
    def get_consent_data_trace(self, consent_id, access_token):
        # implement REST call
        if self.calls_ready:
            if url_to_manager == 'https://smashhit.ari-mobility.eu/api/traceability':
                response = get(url=f'{self.url}/consent_trace/{consent_id}',
                               headers={'x-auth-token': access_token}).json()
            else:
                # access_token is not required to be passed below internally
                response = get(url=f'{self.url}/consent_trace/{consent_id}').json()
        else:
            response = self.traceability_manager.get_consent_data_trace(consent_id)
        return response

    # function to get trace of get trace of data using contract id
    def get_contract_data_trace(self, contract_id, access_token):
        # implement REST call
        if self.calls_ready:
            if url_to_manager == 'https://smashhit.ari-mobility.eu/api/traceability':
                response = get(url=f'{self.url}/contract_trace/{contract_id}',
                               headers={'x-auth-token': access_token}).json()
            else:
                response = get(url=f'{self.url}/contract_trace/{contract_id}').json()
        else:
            # access_token is not required to be passed below internally
            response = self.traceability_manager.get_contract_data_trace(contract_id)
        return response


####### JUST FOR TESTING #########
"""
if __name__ == '__main__':
    manager_caller = TraceabilityManagerCaller(url="http://localhost:5000")
    res = manager_caller.register_data("1", "2", "3", "co_001", "origin", "2020-01-01", "2022-01-01")

    #res = manager_caller.register_data(smashhit_id="8e4f0b25-a05d-11ec-ba17-380025236972", hash_data="abcdwq0eeehg_hash", signed_hash="abcdehg_hash_signed", consent_id="c_002", contract_id="c_002_contract", origin="own_id", creation_time="2022-03-15", expiration_time="2023-03-15")
    print(res)
"""
