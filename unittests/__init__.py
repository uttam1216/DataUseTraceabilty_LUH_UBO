import os
import shutil


def get_prefix():
    root = 'src'
    prefix = ''
    while not os.path.exists(f'{prefix}{root}'):
        prefix = f'../{prefix}'
    return prefix


def clean_keys():
    prefix = get_prefix()
    path_to_keys = f'{prefix}src/keys'
    for filename in os.listdir(path_to_keys):
        file_path = os.path.join(path_to_keys, filename)
        try:
            if 'id_' not in filename and 'own' not in filename and os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def remove_csv_files():
    prefix = get_prefix()
    path_to_utils = f'{prefix}src/utils'
    for filename in os.listdir(path_to_utils):
        file_path = os.path.join(path_to_utils, filename)
        try:
            if '.csv' in filename and os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


if __name__ == '__main__':
    clean_keys()
    remove_csv_files()
