import pandas as pd
import binascii

from flask import Flask, request
from flask_restful import abort, Api, Resource
from apispec import APISpec
from marshmallow import Schema, fields
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec.extension import FlaskApiSpec
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc, use_kwargs
from traceability_module import TraceabilityModule
from util import debug, get_record
from digital_signature import _get_hash
from encryption_module import *
from waitress import serve

app = Flask(__name__)
api = Api(app)
app.config.update({
    'APISPEC_SPEC': APISpec(
        title='Traceability Module',
        version='v1',
        plugins=[MarshmallowPlugin()],
        openapi_version='2.0.0',
        base_url='/',
        host='localhost:5001/',
        schemes='[http]'
    ),
    'APISPEC_SWAGGER_URL': '/swagger/',  # URI to access API Doc JSON
    'APISPEC_SWAGGER_UI_URL': '/swagger-ui/'  # URI to access UI of API Doc
})
docs = FlaskApiSpec(app)


##### SCHEMAS #####

# defining class with input descriptions for register data functionality
class RegisterRequestSchema(Schema):
    consent_id = fields.String(required=True, description="The Consent ID of the consent given by the data owner")
    contract_id = fields.String(required=True, description="The Contract ID of the contract made by the data owner")
    hash = fields.String(required=True, description="Hash of the data to be registered.")
    origin = fields.String(required=False, description="[optional] The origin of the data")
    creation_time = fields.Date(required=False, description="[optional] The creation time of the data")
    expiration_time = fields.Date(required=False,
                                  description="[optional] The expiration time of the consent for the data usage.")

# defining class with input descriptions for register response of data receipt
class RegisterResponseSchema(Schema):
    # signed_hash = fields.String(required=True, description="Signed Hash of the data.") #
    uri = fields.String(required=True, description="URI created by traceability module to track the data.")

# defining class with input descriptions for initiating the transfer of data functionality
class InitTransferRequestSchema(Schema):
    uri = fields.String(required=True, description="URI of the data.")
    receiver_name = fields.String(required=True, description="Smashhit registered name of the receiver of the data.")

# defining class with input descriptions for register response of data receipt
class ConfirmTransferRequestSchema(Schema):
    uri = fields.String(required=True, description="URI of the data.")
    hash = fields.String(required=True, description="Hash of the transferred data.")
    sender_id = fields.String(required=True, description="ID of the sender of the data.")
    signature_of_sender = fields.String(required=True, description="Signature of the sender.")
    # TODO: How can the reciever have this information?

# defining class with input descriptions for fetching data trace based on consent id of registered data
class ConsentDataTraceRequestSchema(Schema):
    consent_id = fields.String(required=True, description="Consent id of the data.")

# defining class with input descriptions for fetching data trace based on contract id of registered data
class ContractDataTraceRequestSchema(Schema):
    contract_id = fields.String(required=True, description="Contract id of the data.")

##### START API ####
def run(own_smashhit_id, url_to_manager, path_to_private_key, path_to_public_key, host='0.0.0.0', port=5001,
        debug=True):
    global TM
    TM = TraceabilityModule(path_to_private_key, path_to_public_key, url_to_manager, own_smashhit_id)
    # app.run(host=host, port=port, debug=debug) # threaded=False, processes=2

    serve(app, host=host, port=port)  # threads=2

# This API is called, when a data provider wants to register a new data set.
# One consent can be used in many contracts, i.e. one to many mapping but reverse cannot happen
#
# Parameters: JSON
# Example
# {
#   'hash': '5h$a/Zd1o?a',
#   'consent_id':'173038173',
#   'contract_id':'173038173_0',
#   'origin':'',
#   'creation_time':'11.06.2021',
#   'expiration_time':'12.06.2022',
# }
#

class Register_data(MethodResource, Resource):
    @doc(description='Register new data set.',
         tags=['Register Data'],
         responses={'200': {'description': 'Data registered'}, '500': {'description': 'Internal Server Error'}})
    @use_kwargs(RegisterRequestSchema, location='json', required=True)
    # @marshal_with(RegisterResponseSchema)
    def post(self, **kwargs):
        try:
            data_specification = request.get_json()

            # Extract data from JSON
            hash = data_specification['hash']
            consent_id = data_specification['consent_id']
            contract_id = data_specification['contract_id']
            origin = data_specification['origin']
            creation_time = data_specification['creation_time']
            expiration_time = data_specification['expiration_time']
            ret = TM.register_data(consent_id, contract_id, hash, origin, creation_time=creation_time,
                                   expiration_time=expiration_time)
            ret_json = {"ERROR": str(ret[2]), "uri": str(ret[1])}
            if ret[2] != "":
                return ret_json, 500
            else:
                return ret_json, 200
        except Exception as e:
            return {"uri": '', "ERROR": str(e)}, 500


# This API is called when a data provider wants to share a data set
#
# Parameters:
# Data ID
# receiver_id

class Init_data_transfer(MethodResource, Resource):
    @doc(description='Initialize Data transfer, by sending a transfer intent regarding the reciever.',
         tags=['Initiate Data Transfer'],
         responses={'200': {'description': 'Transfer initiated'}, '201': {'description': 'Unrecognized receiver'}, '500': {'description': 'Internal Server Error'}})
    @use_kwargs(InitTransferRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            json_body = request.get_json()
            uniform_resource_identifier = json_body['uri']
            # change to be done here to take correct receiver id if it is already available...because
            '''A logic: Receiver name with its uri must be present in records.csv before initiating data transfer 
               because, this field is also used in creating signature of the sender. 
               During confirming the data transfer, again the sender's signature is verified by 
               reforming the sender's signature where again receiver's uri is used.
               So, both times the receiver must be same.'''
            receiver = get_record(json_body['receiver_name'][:-4]) if "_uri" == json_body['receiver_name'][-4:] else get_record(json_body['receiver_name'])
            receiver_name = json_body['receiver_name']
            if receiver is None:
                ret_json = {"message": "Receiver "+receiver_name+" does not use traceability module!",
                            "sender_id": "", "signature_of_sender": ""}
                return ret_json, 201
            receiver_id = receiver["uniform_resource_identifier"]
            receiver_id = str(receiver_id) if not isinstance(receiver_id, str) else receiver_id

            message, sender_id, signature_of_sender = TM.notify_data_transfer(uniform_resource_identifier, str(receiver_id))
            ret_json = {"message": "Data transferred correctly" if message == "" else message,
                            "sender_id": sender_id, "signature_of_sender": signature_of_sender}
            if message == "":
                return ret_json, 200
            else:
                return ret_json, 500
        except Exception as e:
            return {"ERROR": str(e)}, 500


# This API is called when a data requester gets a data set from a data provider
# To finalize the data transfer the data requester confirms that he got the data
#
# Parameters:
# data_id
# data
# sender_id
# reciever_id
# signature_of_sender
#
class Confirm_data_transfer(MethodResource, Resource):
    @doc(description='After recieving data, confirm data transfer by sending a signed hash.',
         tags=['Confirm Data Transfer'],
         responses={'200': {'description': 'Transfer completed'}, '400': {'description': 'Transfer was not initiated'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(ConfirmTransferRequestSchema, location=('json'), required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            uniform_resource_identifier = json_body['uri']
            hash = _get_hash(json_body['hash'])
            sender_id = json_body['sender_id']
            signature_of_sender = json_body['signature_of_sender']

            if debug:
                # sender details are fetched from the records.csv, to have its private and public keys
                sender = get_record(sender_id[:-4]) if "_uri" == sender_id[-4:] else get_record(sender_id)
                # receiver details are fetched from records.csv, to have its private and public keys
                receiver = get_record("receiver")   # need to find a way to remove this hard coding 6th May
                receiver_id = receiver["uniform_resource_identifier"]
                receiver_id = str(receiver_id) if not isinstance(receiver_id, str) else receiver_id
                path_to_private_key_sender = sender["path_to_private_key"]
                private_key_sender = load_private_key(path_to_private_key_sender)
                if "_uri" != sender_id[-4:]:
                    sender_id = sender["uniform_resource_identifier"]
                data_sender = str(uniform_resource_identifier) + str(sender_id) + str(receiver_id)
                data_sender = _get_hash(data_sender)
                signature_of_sender = private_key_sender.sign(data_sender)
                signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii') # hexlify to convert to str
                # Even the above signature works fine in verification, also what exists in transferred_data.csv works

            message = TM.verify_received_data(hash, uniform_resource_identifier, sender_id, signature_of_sender)
            ret_json = {"message": "Data received correctly" if message == "" else message}
            if message == "Data received correctly" or message == '':
                return ret_json, 200
            else:
                return ret_json, 500
        except Exception as e:
            return {"ERROR": str(e)}, 500


# This API is called when a data owner wants to see trace of data against a consent id.
#
# Parameters: consent_id
#
class Consent_data_trace(MethodResource, Resource):
    @doc(description='Data owner requests a data trace. Returns all logs of the data based on the Consent ID',
         tags=['Data Trace'],
         responses={'200': {'description': 'Data trace retrieved'}, '500': {'description': 'Internal Server Error'}})
    # @marshal_with(consentTraceReqSchema)
    @use_kwargs(ConsentDataTraceRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            consent_id = json_body['consent_id']
            ret = TM.get_consent_data_trace(consent_id)
            return ret, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


# This API is called when a data owner wants to see trace of data against a contract id.
#
# Parameters: contract_id
#
class Contract_data_trace(MethodResource, Resource):
    @doc(description='Data owner requests a data trace. Returns all logs of the data based on the Contract ID',
         tags=['Data Trace'],
         responses={'200': {'description': 'Data trace retrieved'}, '500': {'description': 'Internal Server Error'}})
    # @marshal_with(contractTraceReqSchema)
    @use_kwargs(ContractDataTraceRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            contract_id = json_body['contract_id']
            ret = TM.get_contract_data_trace(contract_id)
            return ret, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


# Add Url Path
api.add_resource(Register_data, '/register')
api.add_resource(Init_data_transfer, '/init_transfer')
api.add_resource(Confirm_data_transfer, '/confirm_transfer')
api.add_resource(Consent_data_trace, '/consent_trace')
api.add_resource(Contract_data_trace, '/contract_trace')

# Swagger Docs
docs.register(Register_data)
docs.register(Init_data_transfer)
docs.register(Confirm_data_transfer)
docs.register(Consent_data_trace)
docs.register(Contract_data_trace)