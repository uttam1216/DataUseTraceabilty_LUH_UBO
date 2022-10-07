from src.traceability_manager import api
from src.utils.util import log_path_registered_data, log_path_transferred_data, get_prefix, manager_name, create_record

# main program starts here
if __name__ == '__main__':
    manager = create_record(manager_name)
    path_to_private_key = manager["path_to_private_key"]
    path_to_public_key = manager["path_to_public_key"]

    # call to the api with required parameters
    api.run(log_path_registered_data, log_path_transferred_data, path_to_private_key, path_to_public_key,
            debug=True)

