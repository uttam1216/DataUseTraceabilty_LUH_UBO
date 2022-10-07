from src.traceability_module import api
from src.utils.util_module import url_to_manager, onboard

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--name', type=str, default='VW_Receiver',
                    help='name of the company')  # LUH_UBO_Sender  # LUH_UBO_Receiver  VW_Receiver Traceability App
# set the default value of --name as 'sender' for register data and notify data transfer  functionality - for Testing
# can set the default value of --name as 'receiver' when running for confirm data receipt functionality - for Testing
# In real world application, just need to put company's unique name and then separately send public key to manager
args = parser.parse_args()

if __name__ == '__main__':
    # TODO: Get and fill Parameters from terminal (e.g smashhit_id, url_to_manager, path_to_private_key,
    #  path_to_public_key)

    """
    import argparse
    parser = argparse.ArgumentParser()
    # python src/traceability_module/main.py --smashhit_id vw_uri
    parser.add_argument('--smashhit_id', default='own_smashhit_uri', type=str,
                        help='Id of the company in smashhit')
    args = parser.parse_args()
    own_smashhit_id = args.smashhit_id
    """

    own_smashhit = onboard(args.name, url_to_manager)
    own_smashhit_id = own_smashhit["uniform_resource_identifier"]
    path_to_private_key = own_smashhit["path_to_private_key"]
    path_to_public_key = own_smashhit["path_to_public_key"]
    print(f'{args.name}, your id for data traceability (smashhit_id) is: {own_smashhit_id}')
    # print("Module")
    api.run(own_smashhit_id, url_to_manager, path_to_private_key, path_to_public_key, debug=True)
    # url_to_manager is the url to communicate with the manager for responses
