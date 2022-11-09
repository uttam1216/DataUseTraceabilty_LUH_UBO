import pandas as pd
import binascii
import numpy as np

from flask import Flask, request
from flask_restful import abort, Api, Resource
from apispec import APISpec
from marshmallow import Schema, fields
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec.extension import FlaskApiSpec
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc, use_kwargs

from src.traceability_manager import initialize_records
from src.traceability_module.traceability_module import TraceabilityModule
from src.utils.util_module import log_path_registered_data, debug, get_record, transact_with_db, flag_transact_with_db
from src.utils.digital_signature import _get_hash
from src.utils import encryption_module as em
from src.traceability_module.re_identification_age_trace import AGE_Trace_reidentification
from src.traceability_module.watermark_trip import Watermark_Trajectory
from src.traceability_module.check_watermark_correlation import Watermarking_Correlation
import json
import glob
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
    fingerprint = fields.String(required=True, description="Fingerprint of the data to be registered.")
    origin = fields.String(required=False, description="[optional] The origin of the data")
    creation_time = fields.Date(required=False, description="[optional] The creation time of the data")
    expiration_time = fields.Date(required=False,
                                  description="[optional] The expiration time of the consent for the data usage.")
    access_token = fields.String(required=False, description="The smashHit access token")


# defining class with input descriptions for register response of data receipt
class RegisterResponseSchema(Schema):
    # signed_hash = fields.String(required=True, description="Signed Hash of the data.") #
    uri = fields.String(required=True, description="URI created by traceability module to track the data.")


# defining class with input descriptions for initiating the transfer of data functionality
class InitTransferRequestSchema(Schema):
    uri = fields.String(required=True, description="URI of the data.")
    receiver_name = fields.String(required=True, description="Smashhit registered name of the receiver of the data.")
    access_token = fields.String(required=False, description="The smashHit access token")


# defining class with input descriptions for register response of data receipt
class ConfirmTransferRequestSchema(Schema):
    uri = fields.String(required=True, description="URI of the data.")
    hash = fields.String(required=True, description="Hash of the transferred data.")
    sender_id = fields.String(required=True, description="ID of the sender of the data.")
    signature_of_sender = fields.String(required=True, description="Signature of the sender.")
    access_token = fields.String(required=False, description="The smashHit access token")
    # TODO: How can the reciever have this information?


# defining class with input descriptions for fetching data trace based on consent id of registered data
class ConsentDataTraceRequestSchema(Schema):
    consent_id = fields.String(required=True, description="Consent id of the data.")
    access_token = fields.String(required=False, description="The smashHit access token")


# defining class with input descriptions for fetching data trace based on contract id of registered data
class ContractDataTraceRequestSchema(Schema):
    contract_id = fields.String(required=True, description="Contract id of the data.")
    access_token = fields.String(required=False, description="The smashHit access token")


# defining class with input des for fetching input watermarked trajectory data for checking correlation
class HashingSchema(Schema):
    trip_data = fields.Dict(required=True, description="Data with watermarked trip details: [dict]")


class AGETraceReIdentificationSchema(Schema):
    own_data = fields.List(fields.List(fields.List(fields.Float())), required=True,
                           description="Dataset containing Trajectories: List of Trajectories, List of Points, List containing [lon, lat, time]")
    trajectory = fields.List(fields.List(fields.Float()), required=True,
                             description="Trajectory to re-identify: List of Points, List containing [lon, lat, time]")


class AGETraceRepresentationSchema(Schema):
    trajectory = fields.List(fields.List(fields.Float()), required=True,
                             description="Trajectory to re-identify: List of Points, List containing [lon, lat, time]")


# defining class with input descriptions for fetching input data for watermarking
class WTraceWatermarkingSchema(Schema):
    consent_id = fields.String(required=True, description="Consent id of the data.")
    trip_data = fields.Dict(required=True, description="Data with trip details: [dict]")

# defining class with input descriptions for fetching input watermarked trajectory data for checking correlation
class WTraceCheckCorrelationSchema(Schema):
    consent_id = fields.String(required=False, description="Consent against which correlation needs to be checked")
    watermarked_trip_data = fields.Dict(required=True, description="Data with watermarked trip details: [dict]")


##### START API ####
def run(own_smashhit_id, url_to_manager, path_to_private_key, path_to_public_key, host='0.0.0.0', port=5001,
        debug=True):
    # Initialize Controller: TraceabilityModule
    global TM
    TM = TraceabilityModule(path_to_private_key, path_to_public_key, url_to_manager, own_smashhit_id)
    # app.run(host=host, port=port, debug=debug)
    serve(app, host=host, port=port)


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
            hash = str(data_specification['hash'])
            consent_id = data_specification['consent_id']
            contract_id = data_specification['contract_id']
            origin = data_specification['origin']
            creation_time = data_specification['creation_time']
            expiration_time = data_specification['expiration_time']
            fingerprint = data_specification['fingerprint']
            access_token = data_specification['access_token']
            ret = TM.register_data(consent_id, contract_id, hash, fingerprint, access_token, origin,
                                   creation_time=creation_time, expiration_time=expiration_time)
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
    @doc(description='Initialize Data transfer, by sending a transfer intent regarding the receiver.',
         tags=['Initiate Data Transfer'],
         responses={'200': {'description': 'Transfer initiated'}, '201': {'description': 'Unrecognized receiver'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(InitTransferRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            json_body = request.get_json()
            uniform_resource_identifier = json_body['uri']
            access_token = json_body['access_token']
            # change to be done here to take correct receiver id if it is already available...because
            '''A logic: Receiver name with its uri must be present in records.csv before initiating data transfer 
               because, this field is also used in creating signature of the sender. 
               During confirming the data transfer, again the sender's signature is verified by 
               reforming the sender's signature where again receiver's uri is used.
               So, both times the receiver must be same. '''

            receiver = get_record(json_body['receiver_name'][:-4], access_token) if "_uri" == json_body['receiver_name'][-4:] else get_record(json_body['receiver_name'], access_token)
            receiver_name = json_body['receiver_name']
            # to check presence of this receiver, we should have records table also at Module's end? DOUBT, to be disc.
            if receiver is None:
                ret_json = {"message": "Receiver " + receiver_name + " does not use traceability module!",
                            "sender_id": "", "signature_of_sender": ""}
                return ret_json, 201
            receiver_id = receiver["uniform_resource_identifier"]
            receiver_id = str(receiver_id) if not isinstance(receiver_id, str) else receiver_id


            # only for tests
            if debug:
                initialize_records()
                # receiver = get_record(receiver_id[:-4]) if "_uri" == receiver_id[-4:] else get_record(receiver_id)
                receiver = get_record(json_body['receiver_name'][:-4]) if "_uri" == json_body['receiver_name'][
                                                                                    -4:] else get_record(
                    json_body['receiver_name'])
                receiver_id = receiver["uniform_resource_identifier"]
                receiver_id = str(receiver_id) if not isinstance(receiver_id, str) else receiver_id
                provider = get_record("provider")
                path_to_private_key_provider = provider["path_to_private_key"]
                provider_id = provider["uniform_resource_identifier"]
                private_key_provider = em.load_private_key(path_to_private_key_provider)
                hash_data = b"hash_data"
                signed_hash = private_key_provider.sign(hash_data)
                signed_hash = binascii.hexlify(signed_hash).decode('ascii')  # hexlify to pass as string in json
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
                    data = {
                        'smashhit_id': "provider_uri",
                        'uniform_resource_identifier': uniform_resource_identifier,
                        'hash_data': hash_data,
                        'signed_hash': signed_hash,
                        'consent_id': "c_002",
                        'contract_id': "c_002_contract",
                        'origin': "owner_uri",
                        'creation_time': "2013-03-10",
                        'expiration_time': "2033-03-10"
                    }
                    # start of changes by Uttam on 16 Sep to transact with DB
                    if flag_transact_with_db:
                        obj = transact_with_db()
                        obj.insert_values_in_registered_data(data)
                    else:
                        # end of changes by Uttam on 16 Sep to transact with DB
                        current_log_df = current_log_df.append(data, ignore_index=True)
                        current_log_df.to_csv(log_path_registered_data, index=False)
                # now for sure the data should be registered

            # access token needs to be passed to the header while making request to the manager
            message, sender_id, signature_of_sender = TM.notify_data_transfer(uniform_resource_identifier, access_token,
                                                                              str(receiver_id))
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
    @use_kwargs(ConfirmTransferRequestSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            uniform_resource_identifier = json_body['uri']
            # commented on 19th Sep by Uttam
            # hash = _get_hash(json_body['hash'])
            hash = json_body['hash']
            sender_id = json_body['sender_id']
            signature_of_sender = json_body['signature_of_sender']
            access_token = json_body['access_token']

            if debug:
                initialize_records()
                # sender details are fetched from the records.csv, to have its private and public keys
                sender = get_record(sender_id[:-4]) if "_uri" == sender_id[-4:] else get_record(sender_id)
                # receiver details are fetched from records.csv, to have its private and public keys
                receiver = get_record("receiver")  # need to find a way to remove this hard coding 6th May
                receiver_id = receiver["uniform_resource_identifier"]
                receiver_id = str(receiver_id) if not isinstance(receiver_id, str) else receiver_id
                path_to_private_key_sender = sender["path_to_private_key"]
                private_key_sender = em.load_private_key(path_to_private_key_sender)
                if "_uri" != sender_id[-4:]:
                    sender_id = sender["uniform_resource_identifier"]
                data_sender = str(uniform_resource_identifier) + str(sender_id) + str(receiver_id)
                data_sender = _get_hash(data_sender)
                signature_of_sender = private_key_sender.sign(data_sender)
                signature_of_sender = binascii.hexlify(signature_of_sender).decode('ascii')  # hexlify to convert to str
                # Even the above signature works fine in verification, also what exists in transferred_data.csv works

            # access token needs to be passed to the header while making request to the manager
            message = TM.verify_received_data(hash, uniform_resource_identifier, sender_id, signature_of_sender,
                                              access_token)
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
            access_token = json_body['access_token']
            # access token needs to be passed to the header while making request to the manager
            ret = TM.get_consent_data_trace(consent_id, access_token)
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
            access_token = json_body['access_token']
            # access token needs to be passed to the header while making request to the manager
            ret = TM.get_contract_data_trace(contract_id, access_token)
            return ret, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


class Hash_Json(MethodResource, Resource):
    @doc(description='Data Provider can create hash of the json and use it for registering data.',
         tags=['Hashing'],
         responses={'200': {'description': 'Json data hashed successfully'},
                    '422': {'description': 'Unprocessable input format'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(HashingSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            trip_data = json_body['trip_data']
            # trips_data_dict = trip_data[0]
            data = json.dumps(trip_data, sort_keys=True)  # convert into string
            hash_data = str(hash(data))
            # hash_data = str(hash(data)).encode()  # get hash of string that gives an integer, then cast into string
            # and then encode into byte
            # print('hash of the data is: ', hash_data)

            # return {'result': watermarked_response.to_json()}, 200
            # return {'result': watermarked_response[0]}, 200
            return {'hash': str(hash_data)}, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


# Reidentification
class AGE_Trace_Reidentification(MethodResource, Resource):
    @doc(description='Data Provider can check whether a trajectory is a modified Version of a Trajectory in his Data.',
         tags=['Re-Identification'],
         responses={'200': {'description': 'Re-Identification process successful'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(AGETraceReIdentificationSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            own_data = json_body['own_data']
            trajectory = json_body['trajectory']

            # Convert to numpy
            own_data = np.asarray(own_data)
            trajectory = np.asarray(trajectory)

            # Initialize AGE-Trace Model
            age_trace_model = AGE_Trace_reidentification()
            pred = age_trace_model.re_identify_data(own_data, trajectory)

            return {'result': pred.tolist()}, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


class AGE_Trace_Representation(MethodResource, Resource):
    @doc(description='Creates Fingerprint of data using AGE-trace model.',
         tags=['Re-Identification'],
         responses={'200': {'description': 'Fingerprinting process successful'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(AGETraceRepresentationSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            trajectory = json_body['trajectory']
            # Convert to numpy
            trajectory = np.asarray(trajectory)
            # Initialize AGE-Trace Model and get Fingerprint/Representation
            age_trace_model = AGE_Trace_reidentification()
            fingerprint = age_trace_model.get_trajectory_representation(trajectory)
            # Convert to list format
            res = fingerprint.numpy().tolist()
            return {'result': res}, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


class Watermark_Trip(MethodResource, Resource):
    @doc(description='Data Provider can watermark the trajectory data by injecting his secret watermark.',
         tags=['Re-Identification'],
         responses={'200': {'description': 'Trajectory data watermarked successfully'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(WTraceWatermarkingSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            trip_data = json_body['trip_data']
            consent_id = json_body['consent_id']

            # Initialize W-Trace watermarking Model
            w_trace_model = Watermark_Trajectory()
            watermarked_response = w_trace_model.watermark_trajectory(trip_data, consent_id)

            # return {'result': watermarked_response.to_json()}, 200
            # return {'result': watermarked_response[0]}, 200
            return watermarked_response, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


'''
class Watermarked_Correlation(MethodResource, Resource):
    @doc(description='Data Provider can check whether a trajectory is a modified Version of a Trajectory in his Data.',
         tags=['Re-Identification'],
         responses={'200': {'description': 'Re-Identification process successful'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(WTraceCheckCorrelationSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            watermarked_trip_data = json_body['watermarked_trip_data']

            # Initialize checking of correlation model
            w_trace_correlation = Watermarking_Correlation()
            correlation = w_trace_correlation.get_watermark_correlation(watermarked_trip_data)

            return {'correlation': correlation}, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500
'''

class Watermarked_Correlation(MethodResource, Resource):
    @doc(description='Data Provider can check whether a trajectory is a modified Version of a Trajectory in his Data.',
         tags=['Re-Identification'],
         responses={'200': {'description': 'Possible correlation(s) found successfully'},
                    '500': {'description': 'Internal Server Error'}})
    @use_kwargs(WTraceCheckCorrelationSchema, location='json', required=True)
    def post(self, **kwargs):
        try:
            # Extract data from JSON
            json_body = request.get_json()
            watermarked_trip_data = json_body['watermarked_trip_data']
            consent_id = json_body['consent_id']

            # Initialize checking of correlation model
            w_trace_correlation = Watermarking_Correlation()
            trip_id = watermarked_trip_data['trip_id']
            if consent_id != '' and trip_id != '':
                # load watermarking extracts i.e. x1_fill of that trajectory
                x1_full = np.load(
                    'wtrace_data/intermediate_files/extract_files/' + consent_id + '_c$t_' + trip_id + '_x1_full.npy',
                    allow_pickle=True)
                # load watermark file
                watermark = np.load(
                    'wtrace_data/intermediate_files/watermark_files/' + consent_id + '_c$t_' + trip_id + '_watermark.npy')
                correlation = w_trace_correlation.get_watermark_correlation(watermarked_trip_data, x1_full, watermark)
                res = {'consent_id': consent_id, 'correlation': correlation}
            else:
                # loop through all watermark secret files, finding correlation with each and then present correlation
                res = []
                for fin in glob.glob('wtrace_data/intermediate_files/extract_files/*'):
                    # print('reading file...')
                    sub_res = {}
                    x1_full = np.load(fin, allow_pickle=True)
                    watermark_file_name = fin.replace('extract_files', 'watermark_files').replace('_x1_full.npy', '_watermark.npy')
                    watermark = np.load(watermark_file_name, allow_pickle=True)
                    correlation = w_trace_correlation.get_watermark_correlation(watermarked_trip_data, x1_full,
                                                                                watermark)
                    sub_res['consent_id'] = str(fin.split('_c$t_')[0]).split('/')[-1]
                    sub_res['correlation'] = correlation
                    res.append(sub_res)
            return res, 200
        except Exception as e:
            return {"ERROR": str(e)}, 500


# Add Url Path
api.add_resource(Register_data, '/register')
api.add_resource(Init_data_transfer, '/init_transfer')
api.add_resource(Confirm_data_transfer, '/confirm_transfer')
api.add_resource(Consent_data_trace, '/consent_trace')
api.add_resource(Contract_data_trace, '/contract_trace')
api.add_resource(Hash_Json, '/hash_json')
api.add_resource(AGE_Trace_Reidentification, '/reidentify_fingerprint')
api.add_resource(AGE_Trace_Representation, '/fingerprint_trip')
api.add_resource(Watermark_Trip, '/watermark_trip')
api.add_resource(Watermarked_Correlation, '/watermarked_correlation')

# Swagger Docs
docs.register(Register_data)
docs.register(Init_data_transfer)
docs.register(Confirm_data_transfer)
docs.register(Consent_data_trace)
docs.register(Contract_data_trace)
docs.register(Hash_Json)
docs.register(AGE_Trace_Reidentification)
docs.register(AGE_Trace_Representation)
docs.register(Watermark_Trip)
docs.register(Watermarked_Correlation)
