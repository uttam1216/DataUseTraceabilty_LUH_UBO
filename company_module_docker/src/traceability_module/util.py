import os
import uuid
import pandas as pd
from encryption_module import *
# debug = True
debug = False
calls_ready = True

# url_to_manager = 'http://localhost:5000'
url_to_manager = 'http://smashhit.l3s.uni-hannover.de'

# manager name
manager_name = "manager" if url_to_manager == 'http://localhost:5000' else "remote_manager"
manager_copy = "manager_copy" if url_to_manager == 'http://localhost:5000' else "remote_manager_copy"

# function to fetch the record of an actor present else create
def get_record(actor):
    print('getting record')
    # path_to_records_table = "../this_folder/records_table.csv"
    path_to_records_table = "records_table.csv"
    print('path_to_records_table is: ', path_to_records_table)
    table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
    if os.path.exists(path_to_records_table):
        records_df = pd.read_csv(path_to_records_table)
        print('records already exist')
        print('len of records table df is: ', len(records_df))
    else:
        print('path_to_records_table does not exist, so creating new')
        records_df = pd.DataFrame(columns=table_columns)
    if actor in records_df['actor'].to_list():
        print('actor is present in the records table')
        index = records_df.index[records_df["actor"] == actor][0]
        new_actor = records_df.iloc[index]
        new_actor = new_actor.fillna('').to_dict()
        print('following will be returned: ')
        print(records_df.iloc[index])
        return new_actor
    else:
        print('actor is not present in the records table')

    '''
    # the actor is not present and has to be created
    if debug:
        uniform_resource_identifier = f'{actor}_uri'
    else:
        uniform_resource_identifier = uuid.uuid1()
    print('creating new keys')
    private_key_filename = f'{uniform_resource_identifier}_ed25519'
    # path_to_private_key = f'{path_to_private_keys}/{private_key_filename}'
    path_to_private_key = f'{private_key_filename}'
    public_key_filename = f'{uniform_resource_identifier}_ed25519.pub'
    # path_to_public_key = f'{path_to_public_keys}/{public_key_filename}'
    path_to_public_key = f'{public_key_filename}'
    # creation of keys
    private_key = generate_private_key()
    save_private_key(private_key, private_key_filename)
    public_key = generate_public_key(private_key)
    save_public_key(public_key, public_key_filename)
    # insertion of the new record in table
    new_record = {'actor': actor, 'uniform_resource_identifier': uniform_resource_identifier,
                  'path_to_private_key': path_to_private_key, 'path_to_public_key': path_to_public_key}
    # ignore_index=True to avoid thinking about the index
    records_df = records_df.append(new_record, ignore_index=True)
    records_df = pd.DataFrame(records_df, columns=table_columns)
    print('writing new csv file')
    records_df.to_csv(path_to_records_table, index=False)
    return new_record
    '''
    return None

def create_record(actor):
    record = get_record(actor)
    if record is None:
        path_to_records_table = "records_table.csv"
        table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
        if not os.path.exists(path_to_records_table):
            records_df = pd.DataFrame(columns=table_columns)
        else:
            records_df = pd.read_csv(path_to_records_table)
        # the case if the actor is not present and has to be created
        import uuid

        # path_to_private_keys = f'{prefix}src/keys'
        # path_to_public_keys = f'{prefix}src/keys'
        if debug:
            uniform_resource_identifier = f'{actor}_uri'
        else:
            uniform_resource_identifier = uuid.uuid1()
        private_key_filename = f'{uniform_resource_identifier}_ed25519'
        path_to_private_key = f'{private_key_filename}'
        public_key_filename = f'{uniform_resource_identifier}_ed25519.pub'
        path_to_public_key = f'{public_key_filename}'
        # creation of keys
        private_key = generate_private_key()
        save_private_key(private_key, path_to_private_key)
        public_key = generate_public_key(private_key)
        save_public_key(public_key, path_to_public_key)

        # if actor is local manager, we should create a local copy of the manager
        if actor == "manager":
            save_public_key(public_key, "manager_copy_public_key.pub")

        # insertion of the new record in table
        new_record = {'actor': actor, 'uniform_resource_identifier': str(uniform_resource_identifier),
                      'path_to_private_key': path_to_private_key, 'path_to_public_key': path_to_public_key}
        # ignore_index=True to avoid thinking about the index
        records_df = records_df.append(new_record, ignore_index=True)
        records_df = pd.DataFrame(records_df, columns=table_columns)
        records_df.to_csv(path_to_records_table, index=False)
        return new_record
    return record



# function for boarding of a new company on smashhit's traceability module - still under development
def onboard(name, url):
    from requests import post

    # create and insert the actor inside the module or get existing actor
    result = create_record(name)
    new_data = result.copy()
    new_data["path_to_private_key"] = ""
    new_data["path_to_public_key"] = ""

    # insert the new if not existing yet
    ret = post(url=f'{url}/onboard', json=new_data)
    response = ret.text
    if ret.status_code == 200:  # 200 means new actor, 201 means old actor
        # we send the public key of the module to the manager
        y = open(result["path_to_public_key"], 'rb')
        files = {'file': y}

        x = post(url=f'{url}/key_file', files=files).json()

    # create manager actor with path to the public key corresponding to the existing public key.
    # path_to_manager_public_key = f"{get_prefix()}src/keys/{manager_copy}_public_key.pub"
    path_to_manager_public_key = f"{manager_copy}_public_key.pub"  # uttam 29 July
    manager_record = {'actor': manager_name, 'uniform_resource_identifier': "",
                      'path_to_private_key': "", 'path_to_public_key': path_to_manager_public_key}

    # path_to_records_table = f"{get_prefix()}src/utils/records_table.csv"
    path_to_records_table = "records_table.csv"   # uttam 29 July
    table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
    if not os.path.exists(path_to_records_table):
        records_df = pd.DataFrame(columns=table_columns)
    else:
        records_df = pd.read_csv(path_to_records_table)

    if manager_name not in records_df['actor'].to_list():
        # insert the manager, ignore_index=True to avoid thinking about the index
        records_df = records_df.append(manager_record, ignore_index=True)
        records_df = pd.DataFrame(records_df, columns=table_columns)
        records_df.to_csv(path_to_records_table, index=False)

    # print the response for giving the outcome of onboard process
    print(response)

    return result