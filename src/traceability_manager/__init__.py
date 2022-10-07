import pandas as pd
import os
import uuid
from src.utils import encryption_module as em
from src.utils.util import debug, log_path_registered_data, log_path_transferred_data, registered_data_columns, \
    transferred_data_columns

root = 'src'
prefix = ''
while not os.path.exists(f'{prefix}{root}'):
    prefix = f'../{prefix}'
path_to_private_keys = f'{prefix}src/keys'
path_to_public_keys = f'{prefix}src/keys'


def initialize_records():
    # initialize registered data and transferred data
    registered_data_df = pd.DataFrame(columns=registered_data_columns)
    transferred_data_df = pd.DataFrame(columns=transferred_data_columns)
    if not os.path.exists(log_path_registered_data):
        registered_data_df.to_csv(log_path_registered_data, index=False)
    if not os.path.exists(log_path_transferred_data):
        transferred_data_df.to_csv(log_path_transferred_data, index=False)

    # load the current records table (empty or not)
    path_to_records_table = f"{prefix}src/utils/records_table.csv"
    table_columns = ['actor', 'uniform_resource_identifier', 'path_to_private_key', 'path_to_public_key']
    if os.path.exists(path_to_records_table):
        records_df = pd.read_csv(path_to_records_table)
    else:
        # creation of the table with empty values in case none exists
        records_df = pd.DataFrame(columns=table_columns)

    actors = ['sender', 'receiver', 'manager', 'provider']
    for present in records_df['actor'].to_list():
        try:
            actors.remove(present)
        except:
            # in case records has other elements not present in actors, we do not want to remove them
            pass

    # for each actor we assign a random uniform_resource_identifier, private key and public key
    for actor in actors:
        if debug:
            uniform_resource_identifier = f'{actor}_uri'
        else:
            uniform_resource_identifier = uuid.uuid1()
        private_key_filename = f'{uniform_resource_identifier}_ed25519'
        path_to_private_key = f'{path_to_private_keys}/{private_key_filename}'
        public_key_filename = f'{uniform_resource_identifier}_ed25519.pub'
        path_to_public_key = f'{path_to_public_keys}/{public_key_filename}'
        # creation of keys
        private_key = em.generate_private_key()
        em.save_private_key(private_key, path_to_private_key)
        public_key = em.generate_public_key(private_key)
        em.save_public_key(public_key, path_to_public_key)
        # insertion of the new record in table
        new_record = {'actor': actor, 'uniform_resource_identifier': uniform_resource_identifier,
                      'path_to_private_key': path_to_private_key, 'path_to_public_key': path_to_public_key}
        # ignore_index=True to avoid thinking about the index
        records_df = records_df.append(new_record, ignore_index=True)
        records_df = pd.DataFrame(records_df, columns=table_columns)

    records_df.to_csv(path_to_records_table, index=False)
    return records_df


if __name__ == '__main__':
    df = initialize_records()
    # print(df.head())
