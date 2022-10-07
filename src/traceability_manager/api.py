from flask import Flask, request
from flask_restful import abort, Api, Resource
from apispec import APISpec
from marshmallow import Schema, fields
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec.extension import FlaskApiSpec
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc, use_kwargs
import os
from src.traceability_manager import initialize_records
from src.traceability_manager.traceability_manager import TraceabilityManager, onboard as tm_onboard
from src.utils.util import debug, get_record, log_path_registered_data, get_prefix, transact_with_db, \
    flag_transact_with_db
import pandas as pd
import binascii
from src.utils import encryption_module as em
from src.utils.digital_signature import _get_hash
from waitress import serve

app = Flask(__name__)
api = Api(app)
app.config.update({
    'APISPEC_SPEC': APISpec(
        title='Traceability Manager',
        # description = 'API for the SmashHit Tracebility Manager - Early Prototype',
        version='v1',
        plugins=[MarshmallowPlugin()],
        openapi_version='2.0.0',
        base_url='/',
        host='localhost:5000/',
        schemes='[http]'

    ),
    'APISPEC_SWAGGER_URL': '/swagger/',  # URI to access API Doc JSON
    'APISPEC_SWAGGER_UI_URL': '/swagger-ui/'  # URI to access UI of API Doc
})
docs = FlaskApiSpec(app)


##### SCHEMAS #####
# defining class with input descriptions for register data functionality
class RegisterRequestSchema(Schema):
    smashhit_id = fields.String(required=True, description="")
    hash = fields.String(required=True,
                         description="Hash of the data to be registered.")
    signed_hash = fields.String(required=True, description="Signed Hash of the data to be registered.")
    consent_id = fields.String(required=False, description="The Consent ID of the consent given by the data owner")
    contract_id = fields.String(required=False, description="The Contract ID of the contract created for data sharing.")
    fingerprint = fields.String(required=False)
    origin = fields.String(required=False)
    creation_time = fields.Date(required=False)
    expiration_time = fields.Date(required=False)


# defining class with input descriptions for register response of data receipt
class RegisterResponseSchema(Schema):  # TODO: To be confirmed if anything more is required.
    signed_hash = fields.String(required=True, description="Signed Hash to verify.")
    uri = fields.String(required=True, description="URI created by traceability module to track the data.")


class CheckActorRecord(Schema):
    actor_name = fields.String(required=True, description="To check presence of an actor in central manager records.")


# defining class with input descriptions for initiating the transfer of data functionality
class InitTransferRequestSchema(Schema):
    uri = fields.String(required=True, description="URI of the data.")
    sender_id = fields.String(required=True, description="ID of the sender of the data.")
    receiver_id = fields.String(required=True, description="ID of the receiver of the data.")
    signature_of_sender = fields.String(required=True, description="Signature of sender.")


# defining class with input descriptions for confirming the receipt of transferred data functionality
class ConfirmTransferRequestSchema(Schema):
    uri = fields.String(required=True, description="URI of the data.")
    hash = fields.String(required=True, description="Hash of the transferred data.")
    sender_id = fields.String(required=True, description="ID of the sender of the data.")
    receiver_id = fields.String(required=True, description="ID of the receiver of the data.")
    signature_of_sender = fields.String(required=True, description="Signature of the sender.")
    signature_of_receiver = fields.String(required=True, description="Signature of the receiver.")


# defining class with input descriptions for onboard functionality
class OnboardRequestSchema(Schema):
    actor = fields.String(required=True, description="Name of the new company that want to use traceability")
    uniform_resource_identifier = fields.String(required=False,
                                                description="identifier of the new company")
    path_to_private_key = fields.String(required=False, description="")
    path_to_public_key = fields.String(required=False, description="")


# defining class with input descriptions for fetching data trace based on consent id of registered data
class ConsentTraceRequestSchema(Schema):
    consent_id = fields.String(required=True, description="Consent id of the data.")


# defining class with input descriptions for fetching data trace based on contract id of registered data
class ContractTraceRequestSchema(Schema):
    contract_id = fields.String(required=True, description="Contract id of the data.")


# It can be a collection of traces: set many to true
consentTraceReqSchema = ConsentTraceRequestSchema(many=True)

# It can be a collection of traces: set many to true
contractTraceReqSchema = ContractTraceRequestSchema(many=True)

# It can be a collection of actors: set many to true
CheckActorRecord = CheckActorRecord(many=True)


##### START API ####
def run(log_path_registered_data, log_path_transferred_data, path_to_private_key, path_to_public_key, host='0.0.0.0',
        port=5000, debug=True):
    global TM
    TM = TraceabilityManager(log_path_registered_data, log_path_transferred_data, path_to_private_key,
                             path_to_public_key)
    # app.run(host=host, port=port, debug=debug)
    serve(app, host=host, port=port)


# This API is called, when a data provider wants to register a new data set.
#
# Parameters: JSON
# Example
# {
#   'smashhit_id':'0001',
#   'hash': '5h$a/Zd1o?a',
#   'signed_hash':'',
#   'consent_id':'173038173',
#   'origin':'',
#   'creation_time':'11.06.2021',
#   'expiration_time':'12.06.2022',
# }
#
class Register_data(MethodResource, Resource):
    @doc(
        description='<b>Register new data set.</b> </br></br> <b>JSON Body specification:</b> </br></br>    <table><tr><th>Variable</th><th>Type</th><th>Provenance</th><th>Description</th></tr><tr><td>smashhit_id</td><td>UUID from module uuid. e.g: import uuid // uri  uuid.uuid1()</td><td>created by the T. Manager when a new entity (company / private) registers to use Data Use Traceability. After the creation, it is sent to that entity</td><td>public id of the company receiving directly the data from the data owner</td></tr><tr><td>hash data</td><td>bytes</td><td>created by the company that has the data and wants to register it.</td><td>the hash of the data content </td></tr><tr><td>signed hash</td><td>bytes</td><td>Internally computed by the T. Module during the registration phase.</td><td>the signature of the hash data, using the private key of the data owner</td></tr><tr><td>consent id</td><td>Any</td><td>Part of the contract information. Refer to the creation of contracts</td><td>identifier of the consent present in the contract signed by the data owner and the company.</td></tr><tr><td>contract id</td><td>Any</td><td>Part of the contract information. Refer to the creation of contracts</td><td>identifier of the contract signed by the data owner and the company about how the data should be used.</td></tr><tr><td>origin</td><td>Any</td><td>Part of the contract information. Refer to the creation of contracts</td><td>id of the data owner</td></tr><tr><td>creation time</td><td>datetime format YYYY-MM-DD</td><td>Part of the contract information. Refer to the creation of contracts</td><td>time at which the data was created.</td></tr><tr><td>expiration time</td><td>datetime format YYYY-MM-DD</td><td>Part of the contract information. Refer to the creation of contracts</td><td>time up to which all the companies in possession of that data are allowed to use it, as defined by contract with the data owner.</td></tr></table>',
        tags=['Register Data'],
        responses={'200': {'description': 'Data registered'}, '500': {'description': 'Internal Server Error'}})
    @use_kwargs(RegisterRequestSchema, location='json', required=True)
    # @marshal_with(RegisterResponseSchema)
    def post(self, **kwargs):
        """
        description: Register new data set
        responses:
            200:
                content:
                    application/json:
                        schema: RegisterResponseSchema
            500:
                description: Internal Server Error
        """
        try:
            data_specification = request.get_json()
            # Extract data from JSON
            smashhit_id = data_specification['smashhit_id']
            hash = data_specification['hash']
            signed_hash = data_specification['signed_hash']
            consent_id = data_specification['consent_id']
            contract_id = data_specification['contract_id']
            fingerprint = data_specification['fingerprint']
            origin = data_specification['origin']
            creation_time = data_specification['creation_time']
            expiration_time = data_specification['expiration_time']

            # For testing
            if debug:
                initialize_records()
                smashhit = get_record(smashhit_id[:-4]) if "_uri" == smashhit_id[-4:] else get_record(smashhit_id)
                path_to_private_key_smashhit = smashhit["path_to_private_key"]
                smashhit_id = smashhit["uniform_resource_identifier"]
                private_key_smashhit = em.load_private_key(path_to_private_key_smashhit)
                signed_hash = private_key_smashhit.sign(hash)
                signed_hash = binascii.hexlify(signed_hash).decode('ascii')
                fingerprint = str(fingerprint)

            ret = TM.register_data(smashhit_id, hash, signed_hash, consent_id, contract_id, fingerprint, origin,
                                   creation_time, expiration_time)
            # the signed hash above refers to the signature done by manager on hash of the data provided by sender
            ret_json = {"uri": str(ret[1]), "signed_hash": str(ret[0]), "ERROR": str(ret[2])}
            if ret[2] != "":
                return ret_json, 500
            else:
                return ret_json, 201
        except Exception as e:
            return {"uri": str(e).split(': ')[1].strip(), "signed_hash": '',
                    "ERROR": str(e).split(': ')[0].strip()}, 500


class Check_actor(MethodResource, Resource):
    # this API is called to check if an actor is preset in the central data storage
    @doc(
        description='<b>Check for presence of an actor in records.</b> </br></br>',
        tags=['Check Actor'],
        responses={'200': {'description': 'True/False'}, '500': {'description': 'Internal Server Error'}})
    def get(self, actor_name):
        try:
            resp = TM.check_actor_name(actor_name)
            # print(resp)
            try:
                res = eval(resp)
            except Exception as ex:
                res = resp
                # print(ex)
            finally:
                return res, 200
        except Exception as e:
            return {"Message": str(e)}, 500


# This API is called when a data provider wants to share a data set
#
# Parameters:
# Data ID
# sender_id
# receiver_id
# signature_of_sender
#
class Init_data_transfer(MethodResource, Resource):
    @doc(
        description='<b>Initialize Data transfer, by sending a transfer intent with information about: sender, reciever, signature_of_sender. </b> </br></br> <b>JSON Body specification:</b> </br></br> <table><tr><th>Variable</th><th>Type</th><th>Provenance</th><th>Description</th></tr><tr><td>uri</td><td>UUID from module uuid. e.g: import uuid // uri  uuid.uuid1()</td><td>Created by tde Manager during the registration process and return to the company registering the data. Eventually received together with the raw data from a previous sender</td><td>id of the data created during the registration process</td></tr><tr><td>sender id</td><td>UUID from module uuid. e.g: import uuid // uri  uuid.uuid1()</td><td>It is one of the attributes of the T. Module, it is picked during the init transfer phase</td><td>id of the company A that wants to send the data</td></tr><tr><td>receiver id</td><td>UUID from module uuid. e.g: import uuid // uri  uuid.uuid1()</td><td>Directly reqiested from the receiver by any mean. E.g by email</td><td>id of the company B to which the data should be sent</td></tr><tr><td>signature of sender</td><td>bytes</td><td>Internally computed by the T. Module during the init transfer phase and returned to the sender as output.</td><td>signature of the <hash data> present in the data registered, using the private key of the sender</td></tr></table>',
        tags=['Initiate Data Transfer'],
        responses={'200': {'description': 'Transfer initiated'}, '500': {'description': 'Internal Server Error'}})
    @use_kwargs(InitTransferRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            json_body = request.get_json()
            uniform_resource_identifier = json_body['uri']
            sender_id = json_body['sender_id']
            receiver_id = json_body['receiver_id']
            signature_of_sender = json_body['signature_of_sender']

            # For testing hash the data and sign hash
            if debug:
                initialize_records()
                sender = get_record(sender_id[:-4]) if "_uri" == sender_id[-4:] else get_record(sender_id)
                path_to_private_key_sender = sender["path_to_private_key"]
                private_key_sender = em.load_private_key(path_to_private_key_sender)
                if "_uri" != sender_id[-4:]:
                    sender_id = sender["uniform_resource_identifier"]
                if "_uri" != receiver_id[-4:]:
                    receiver = get_record(receiver_id[:-4]) if "_uri" == receiver_id[-4:] else get_record(receiver_id)
                    receiver_id = receiver["uniform_resource_identifier"]

                # we verify if the data is already registered, otherwise we register it
                # start of changes by Uttam on 16 Sep to transact with DB
                if flag_transact_with_db:
                    obj = transact_with_db()
                    current_log_df = obj.fetch_records_in_df('registered_data')
                else:
                    # end of changes by Uttam on 16 Sep to transact with DB
                    current_log_df = pd.read_csv(log_path_registered_data)
                    record_indexes = current_log_df.index[
                        (current_log_df['uniform_resource_identifier'] == uniform_resource_identifier)]
                if len(record_indexes) == 0:
                    hash_data = b"hash_data"
                    signed_hash = private_key_sender.sign(hash_data)
                    signed_hash = binascii.hexlify(signed_hash).decode('ascii')
                    ret = TM.register_data(sender_id, hash_data, signed_hash, "c_1234", "owner_uri", "2020-03-10",
                                           "2030-03-10")
                    uniform_resource_identifier = ret[1]
                    if ret[2] != "":
                        return {"ERROR": ret[2]}, 500
                # now for sure the data should be registered
                data_sender = _get_hash(uniform_resource_identifier + sender_id + receiver_id)
                signature_of_sender = private_key_sender.sign(data_sender)
                signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')

            message = TM.notify_data_transfer(uniform_resource_identifier, sender_id, receiver_id, signature_of_sender)

            ret_json = {"message": "Data transferred correctly" if message == "" else message}
            if message == "":
                return ret_json, 200
            else:
                return ret_json, 500
        except Exception as e:
            return {"message": str(e)}, 500


# This API is called when a data requester gets a data set from a data provider
# To finalize the data transfer the data requester confirms that he got the data
#
# Parameters:
# data_id
# signed_hash
#
class Confirm_data_transfer(MethodResource, Resource):
    @doc(
        description='<b>After recieving data, confirm data transfer by sending a signed hash.</b> </br></br> <b>JSON Body specification:</b> </br></br>  <table><tr><th>Variable</th><th>Type</th><th>Provenance</th><th>Description</th></tr><tr><td>uri</td><td>UUID from module uuid. e.g: import uuid // uri  uuid.uuid1()</td><td>Created by the Manager during the registration process and return to the company registering the data. Eventually received together with the raw data from a previous sender</td><td>id of the data created during the registration process</td></tr><tr><td>sender id</td><td>UUID from module uuid. e.g: import uuid // uri  uuid.uuid1()</td><td>Sent to the receiver together with the raw data of after using any mean</td><td>id of the company B to which the data should be sent</td></tr><tr><td>receiver id</td><td>UUID from module uuid. e.g: import uuid // uri  uuid.uuid1()</td><td>It is one of the attributes of the T. Module, it is picked during the init transfer phase</td><td>id of the company A that wants to send the data</td></tr><tr><td>signature of sender</td><td>bytes</td><td>Sent to the receiver together with the raw data of after using any mean</td><td>signature of the <hash data> present in the data registered, using the private key of the sender</td></tr><tr><td>signature of receiver</td><td>bytes</td><td>Internally computed by the T. Module during the confirm transfer phase</td><td>signature of the <hash data> present in the data registered, using the private key of the receiver</td></tr></table>',
        tags=['Confirm Data Transfer'],
        responses={'200': {'description': 'Transfer completed'}, '400': {'description': 'Transfer was not initiated'},
                   '500': {'description': 'Internal Server Error'}})
    @use_kwargs(ConfirmTransferRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            uniform_resource_identifier = json_body['uri']
            hash = _get_hash(json_body['hash'])
            sender_id = json_body['sender_id']
            receiver_id = json_body['receiver_id']
            signature_of_sender = json_body['signature_of_sender']
            signature_of_receiver = json_body['signature_of_receiver']

            # For testing hash the data and sign hash
            if debug:
                initialize_records()
                sender = get_record(sender_id[:-4]) if "_uri" == sender_id[-4:] else get_record(sender_id)
                receiver = get_record(receiver_id[:-4]) if "_uri" == receiver_id[-4:] else get_record(receiver_id)
                path_to_private_key_sender = sender["path_to_private_key"]
                private_key_sender = em.load_private_key(path_to_private_key_sender)
                path_to_private_key_receiver = receiver["path_to_private_key"]
                private_key_receiver = em.load_private_key(path_to_private_key_receiver)
                if "_uri" != sender_id[-4:]:
                    sender_id = sender["uniform_resource_identifier"]
                if "_uri" != receiver_id[-4:]:
                    receiver = get_record(receiver_id[:-4]) if "_uri" == receiver_id[-4:] else get_record(receiver_id)
                    receiver_id = receiver["uniform_resource_identifier"]

                data_sender = uniform_resource_identifier + sender_id + receiver_id
                data_sender = _get_hash(data_sender)
                signature_of_sender = private_key_sender.sign(data_sender)
                signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')
                data_receiver = uniform_resource_identifier + sender_id + receiver_id + signature_of_sender + str(hash)
                data_receiver = _get_hash(data_receiver)
                signature_of_receiver = private_key_receiver.sign(data_receiver)
                signature_of_receiver = binascii.hexlify(signature_of_receiver).decode('ascii')

            message = TM.verify_received_data(hash, uniform_resource_identifier, sender_id, receiver_id,
                                              signature_of_sender, signature_of_receiver)

            ret_json = {"message": "Data received correctly" if message == "" else message}
            if message == "":
                return ret_json, 200
            else:
                return ret_json, 500
        except Exception as e:
            return {"message": str(e)}, 500


# This API is called when a data owner wants to see his data trace.
#
# Parameters: consent_id
#
class Consent_data_trace(MethodResource, Resource):
    @doc(description='Data owner requests a data trace. Returns all logs of the data based on the Consent ID',
         tags=['Data Trace'],
         responses={'200': {'description': 'Data trace retrieved'}, '500': {'description': 'Internal Server Error'}})
    # @marshal_with(consentTraceReqSchema)
    def get(self, consent_id):
        try:
            ret = TM.get_consent_data_trace(consent_id)
            return ret, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


# This API is called when a data owner wants to see his data trace based on contract_id.
#
# Parameters: contract_id
#
class Contract_data_trace(MethodResource, Resource):
    @doc(
        description='Data owner requests a data trace based on contract id. Returns all logs of the data based on the Contract ID',
        tags=['Data Trace'],
        responses={'200': {'description': 'Data trace retrieved'}, '500': {'description': 'Internal Server Error'}})
    # @marshal_with(contractTraceReqSchema)
    def get(self, contract_id):
        try:
            ret = TM.get_contract_data_trace(contract_id)
            return ret, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


class Onboard(MethodResource, Resource):
    @doc(description='Process of having a new company in smashhit',
         tags=['Onboard'],
         responses={'200': {'description': 'Welcome on board to use Data Use Traceability'},
                    '201': {'description': 'You are already on board'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(OnboardRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            actor = f"remote_{json_body['actor']}"
            uniform_resource_identifier = json_body['uniform_resource_identifier']
            path_to_public_key_module = f"{get_prefix()}src/keys/remote_{uniform_resource_identifier}_ed25519.pub"

            # verify if the actor already exists inside the manager
            ret = tm_onboard(actor)

            path_to_records_table = f"{get_prefix()}src/utils/records_table.csv"
            table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
            # start of changes by Uttam on 16 Sep to transact with DB
            if flag_transact_with_db:
                obj = transact_with_db()
                records_df = obj.fetch_records_in_df('records')
            else:
                if not os.path.exists(path_to_records_table):
                    records_df = pd.DataFrame(columns=table_columns)
                else:
                    records_df = pd.read_csv(path_to_records_table)

            module_record = {'actor': actor, 'uniform_resource_identifier': uniform_resource_identifier,
                             'path_to_private_key': "", 'path_to_public_key': path_to_public_key_module}

            ret_json = {}
            if not ret["already_present"]:
                # start of changes by Uttam on 16 Sep to transact with DB
                if flag_transact_with_db:
                    obj = transact_with_db()
                    obj.insert_values_in_records(module_record)
                else:
                    # end of changes by Uttam on 16 Sep to transact with DB
                    # insert record in actors of Manager
                    # ignore_index=True to avoid thinking about the index
                    records_df = records_df.append(module_record, ignore_index=True)
                    records_df = pd.DataFrame(records_df, columns=table_columns)
                    records_df.to_csv(path_to_records_table, index=False)
                ret_json["message"] = "Welcome on board to use Data Use Traceability"
                status = 200
            else:
                module_record = ret["module_record"]
                # drop record in actors because it will be inserted again (to avoid duplicate row)
                indexes = records_df.index[records_df["actor"] == actor]
                records_df = records_df.drop(indexes)
                ret_json["message"] = "You are already on board"
                status = 201

            # Todo: get public key of manager and send it back to the module (for the moment, we insert it directly
            #  inside the module package, so each company will have it by default and as long as it does not change,
            #  it should work)

            return ret_json, status
        except Exception as e:
            return {"ERROR": str(e)}, 500


class Key_file(MethodResource, Resource):
    @doc(description='Process of having a new company in smashhit',
         tags=['Key file'],
         responses={'200': {'description': 'File inserted correctly'},
                    '201': {'description': 'File not inserted'},
                    '500': {'description': 'Internal Server Error'}})
    def post(self, **kwargs):
        try:
            from cryptography.hazmat.primitives.asymmetric import ed25519

            files = request.files
            path_to_public_key_module = f'{get_prefix()}src/keys/remote_{files["file"].filename}'

            # save file
            files["file"].save(path_to_public_key_module)

            return {"message": "File inserted correctly"}, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


# Add Url Path
api.add_resource(Register_data, '/register')
api.add_resource(Init_data_transfer, '/init_transfer')
api.add_resource(Confirm_data_transfer, '/confirm_transfer')
api.add_resource(Consent_data_trace, '/consent_trace/<consent_id>')
api.add_resource(Contract_data_trace, '/contract_trace/<contract_id>')
api.add_resource(Onboard, '/onboard')
api.add_resource(Key_file, '/key_file')
api.add_resource(Check_actor, '/check_actor/<actor_name>')

# Swagger Docs
docs.register(Register_data)
docs.register(Init_data_transfer)
docs.register(Confirm_data_transfer)
docs.register(Consent_data_trace)
docs.register(Contract_data_trace)
docs.register(Check_actor)
