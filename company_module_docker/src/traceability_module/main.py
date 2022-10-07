from api import *
from util import url_to_manager, onboard

if __name__ == '__main__':
    # TODO: Get and fill Parameters
    import argparse
    parser = argparse.ArgumentParser()

    # default value in the following line will be either sender or receiver as per role of the company
    parser.add_argument('--smashhit_name', default='UBO_sender', type=str, help='Name of the company in smashhit') # UBO_sender # UBO_receiver
    parser.add_argument('--url_to_manager', default=url_to_manager, type=str, help='URL at which manager is running')
    args = parser.parse_args()

    # TODO: Get and fill Parameters
    own_smashhit = onboard(args.smashhit_name, url_to_manager)
    print('Running the company module as ', args.smashhit_name)
    url_to_manager = args.url_to_manager
    print('url to the manager for communication is: ', url_to_manager)
    own_smashhit_id = own_smashhit["uniform_resource_identifier"]
    path_to_private_key = own_smashhit["path_to_private_key"]
    path_to_public_key = own_smashhit["path_to_public_key"]
    run(own_smashhit_id, url_to_manager, path_to_private_key, path_to_public_key, debug=True)


