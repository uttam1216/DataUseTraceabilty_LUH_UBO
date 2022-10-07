import os
import pandas as pd
from requests import post, put, get
import binascii
from encryption_module import *
from digital_signature import DigitalSignature, _get_hash
from util import calls_ready, manager_name, manager_copy

# defining a class for the module with various functionalities
class TraceabilityModule:
    def __init__(self, path_to_private_key, path_to_public_key, url_to_manager, own_smashhit_id):
        # TODO read public key
        public_key = load_public_key(path_to_public_key)
        print('path_to_public_key of this module is: ', path_to_public_key)
        # TODO read private key (using passphrase)
        private_key = load_private_key(path_to_private_key)

        self.own_smashhit_id = own_smashhit_id
        print('own_smashhit_id is:', self.own_smashhit_id )

        self.own_signature = DigitalSignature(private_key=private_key, public_key=public_key)

        self.manager_caller = TraceabilityManagerCaller(url=url_to_manager)

    # function to register the data by passing it to the manager
    def register_data(self, consent_id, contract_id, hash_data, origin=None, creation_time=None, expiration_time=None,
                      path_to_records_table="records_table.csv"):
        if isinstance(hash_data, str):
            hash_data = _get_hash(hash_data)

        # we assume that the hash_data already contains everything necessary (data and eventually metadata)
        signed_hash = self.own_signature.sign_data(hash_data)
        encoded_sign = binascii.hexlify(signed_hash).decode('ascii')
        result = self.manager_caller.register_data(
            smashhit_id=self.own_smashhit_id,
            hash_data=hash_data,
            signed_hash=encoded_sign,
            consent_id=consent_id,
            contract_id=contract_id,
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
        public_key_manager = load_public_key(path_to_public_key_manager)
        signed_hash_manager = binascii.unhexlify(signed_hash_manager)
        try:
            public_key_manager.verify(signature=signed_hash_manager, data=hash_data)  # or signed_hash should be passed?
        except Exception as ex:
            result[2] = ex if isinstance(ex, str) else 'Failed to verify manager signature in traceability module'
        return result

    # function to notify that a company which registered the data, now wants to transfer the data
    def notify_data_transfer(self, uniform_resource_identifier, receiver_id):
        other_data = str(uniform_resource_identifier) + str(self.own_smashhit_id) + str(receiver_id)
        signed_data = self.own_signature.sign_data(data=_get_hash(other_data))
        signed_data = binascii.hexlify(signed_data).decode('ascii')

        # TODO @Stefan in the sequence diagram we have in addition a certificate, is that different from the signature?
        # steve: the presence or not of the certificate probably depends on the encryption technology used, though
        # not very sure. It contains the information about sender, reciever, data & a signature so it was not tempered

        # TODO asyncronous call?
        # We don't want to wait on the completion of the following statement
        result = self.manager_caller.notify_data_transfer(uniform_resource_identifier=uniform_resource_identifier,
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
                             signature_of_sender):
        # stores the received data for future use
        """
        Since data in clear (without hash) shouldn't be present on the smashhit platform, we assume that the company
        receives the data and metadata directly from the sender and stores it internally. the hash is sent to the
        receiver through the platform to allow smashhit to monitor the data flow.
        """

        # recompute the hash of data with metadata

        # self.own_smashhit_id value is taken from the main.py of module, whether it be own_smashhit_uri or sender_uri or receiver_uri
        # once test with commenting above line of code -TESTED....VERY IMP. to have correct id here...

        # add own signature
        hash_data = str(hash_data) if isinstance(hash_data, bytes) else hash_data
        receiver_data = str(uniform_resource_identifier) + str(sender_id) + str(self.own_smashhit_id) + str(signature_of_sender) + str(hash_data)
        signature_of_receiver = self.own_signature.sign_data(receiver_data)
        signature_of_receiver = binascii.hexlify(signature_of_receiver).decode('ascii')

        # call manager to check the block
        return self.manager_caller.verify_received_data(hash_data=hash_data,
                                                        uniform_resource_identifier=uniform_resource_identifier,
                                                        sender_id=sender_id,
                                                        receiver_id=self.own_smashhit_id,
                                                        signature_of_sender=signature_of_sender,
                                                        signature_of_receiver=signature_of_receiver)

    # function to call the manager to get the trace of data based on consent id used during registration
    def get_consent_data_trace(self, consent_id):
        # add in the documentation for smashHit platform that we assume that the check who can get which traces
        # is NOT done here
        return self.manager_caller.get_consent_data_trace(consent_id)

    # function to call the manager to get the trace of data based on contract id used during registration
    def get_contract_data_trace(self, contract_id):
        # add in the documentation for smashHit platform that we assume that the check who can get which traces
        # is NOT done here
        return self.manager_caller.get_contract_data_trace(contract_id)


class TraceabilityManagerCaller:
    def __init__(self, url):
        """
        REST Wrapper around the calls
        """
        self.url = url
        self.calls_ready = calls_ready

        """
        To avoid that the module creates an instance of the real manager in case the calls are not ready, we are going 
        to wrap a controller. The controller is the only one knowing how to access all the keys, all the 
        companies identifiers, how to get any information stored by any actor in the platform (included platform 
        database)
        """

    # function to call the manager to get the data registered
    def register_data(self, smashhit_id, hash_data, signed_hash, consent_id, contract_id, origin, creation_time, expiration_time):
        # implement REST call

        new_data = {
            'smashhit_id': str(smashhit_id),
            'hash': str(hash_data) if not isinstance(hash_data, str) else hash_data,
            'signed_hash': str(signed_hash) if not isinstance(signed_hash, str) else signed_hash,
            'consent_id': str(consent_id),
            'contract_id': str(contract_id),
            'origin': str(origin),
            'creation_time': str(creation_time),
            'expiration_time': str(expiration_time)
        }

        if self.calls_ready:
            response = post(url=f'{self.url}/register', json=new_data).json()
        else:
            response = self.traceability_manager.register_data(smashhit_id, hash_data, signed_hash, consent_id,
                                                               contract_id, origin, creation_time, expiration_time)

        # Conversion of json dict to list
        lst_response = [response["signed_hash"], response["uri"], response['ERROR']]
        response = lst_response
        # End of conversion of json dict to list
        return response

    # function to call the manager to notify about the data transfer from company A to company B
    def notify_data_transfer(self, uniform_resource_identifier, sender_id, receiver_id, signature_of_sender):
        # implement REST call
        print('Data to be registered: ')
        print('uri is:', uniform_resource_identifier)
        print('sender_id is:', sender_id)
        print('receiver_id is:', receiver_id)
        print('signature_of_sender is:', signature_of_sender)
        data = {
            'uri': uniform_resource_identifier,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'signature_of_sender': signature_of_sender
        }
        if self.calls_ready:
            result = post(url=f'{self.url}/init_transfer', json=data)
            message = result.json()["message"]
            response = "" if result.status_code != 500 else message
        else:
            response = self.traceability_manager.notify_data_transfer(uniform_resource_identifier, sender_id,
                                                                      receiver_id, signature_of_sender)
            # print(f'res type: {type(response)}, res len: {len(response)} \n', response)
            #response = self.traceability_manager.notify_data_transfer(uniform_resource_identifier, sender_id, receiver_id, signature_of_sender)
            #print('Manager is not running on server to handle requests from the Module')
            #response = '401'
        return response

    # function to call the manager to get the confirmation that the data has been received by the recipient
    def verify_received_data(self, hash_data, uniform_resource_identifier, sender_id, receiver_id,
                             signature_of_sender, signature_of_receiver=None):
        # implement REST call

        new_data = {
            'uri': uniform_resource_identifier,
            'hash': str(hash_data) if not isinstance(hash_data, str) else hash_data,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'signature_of_sender': signature_of_sender,
            'signature_of_receiver': signature_of_receiver
            }
        if self.calls_ready:
            result = post(url=f'{self.url}/confirm_transfer', json=new_data)
            message = result.json()["message"]
            response = "" if result.status_code != 500 else message
        else:
            response = self.traceability_manager.verify_received_data(hash_data, uniform_resource_identifier, sender_id,
                                                                      receiver_id,
                                                                      signature_of_sender, signature_of_receiver)

        return response

    # function to call the manager to get the trace of data based on consent id used during registration
    def get_consent_data_trace(self, consent_id):
        # implement REST call
        if self.calls_ready:
            response = get(url=f'{self.url}/consent_trace/{consent_id}').json()
        else:
            response = self.traceability_manager.get_consent_data_trace(consent_id)
        return response

    # function to call the manager to get the trace of data based on contract id used during registration
    def get_contract_data_trace(self, contract_id):
        # implement REST call
        if self.calls_ready:
            response = get(url=f'{self.url}/contract_trace/{contract_id}').json()
        else:
            response = self.traceability_manager.get_contract_data_trace(contract_id)
        return response