import uuid
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# function to generate the private key
def gen_key():
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key

# function to save the private key
def save_private_key(private_key, filename):
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(filename, 'wb') as pem_out:
        pem_out.write(pem)

# function to save the public key
def save_public_key(public_key, filename):
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    with open(filename, 'wb') as pem_out:
        pem_out.write(pem)

# function to load the private key
def load_private_key(filename):
    with open(filename, 'rb') as pem_in:
        pemlines = pem_in.read()
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(pemlines)
    return private_key

# function to load the public key
def load_public_key(filename):
    with open(filename, 'rb') as pem_in:
        pemlines = pem_in.read()
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(pemlines)
    return public_key

# following code when run, save the keys, sign using the keys and verifies the signature
if __name__ == '__main__':
    '''
    # generate private
    generated_private_key = gen_key()
    # save and load private
    filename_private = '../keys/own_uri_ed25519'
    save_private_key(generated_private_key, filename_private)
    loaded_private_key = load_private_key(filename_private)

    # repeat above for public
    generated_public_key = generated_private_key.public_key()
    filename_public = '../keys/own_uri_ed25519.pub'
    save_public_key(generated_public_key, filename_public)
    loaded_public_key = load_public_key(filename_public)

    message = b"my authenticated message"
    # message = [0, 1, 3]

    # sign with both keys
    original_sign = generated_private_key.sign(message)
    loaded_sign = loaded_private_key.sign(message)

    print(original_sign)
    print(loaded_sign)
    print(original_sign == loaded_sign)

    # check with both keys
    print(generated_public_key.verify(original_sign, message))
    print(loaded_public_key.verify(original_sign, message))

    # check if another key and another signature raises InvalidSignature
    second_key = gen_key()
    different_sign = second_key.sign(message)

    try:
        loaded_public_key.verify(different_sign, message)
    except InvalidSignature:
        print("As expected wrong signature")

    # check if other way fails too
    try:
        second_key.public_key().verify(original_sign, message)
    except InvalidSignature:
        print("As expected wrong signature")
    '''

    from digital_signature import _get_hash
    import encryption_module as em
    path_to_private_key = '../../src/keys/de627352-cc7f-11ec-af24-8da70bfcced8_ed25519'
    path_to_public_key = '../../src/keys/de627352-cc7f-11ec-af24-8da70bfcced8_ed25519.pub'
    private_key_sender = em.load_private_key(path_to_private_key)
    public_key_sender = em.load_public_key(path_to_public_key)

    uri_of_registered_data = 'e9575a84-cc7f-11ec-af24-8da70bfcced8'
    receiver_id = 'receiver'
    signed_data = b'\x12\xc1\x8d\x94\xcf)Q\xcdqA\xe9\x0eQ\xfa5\x01$\xfc\xa8j\xd1\xbc\xa9S,=\xd2\x02\x9c\xf66\x8a\xfb`\xb6\xc8P\x9a\xdf\xf4\x97\x98\xff\xebp\x1b-a$]\xbd\xa8\xf3\x1bO\xd1\xc7\xe9\xb6V\xf1(U\x05'
    sender_id = 'de627352-cc7f-11ec-af24-8da70bfcced8'
    #data = (uri_of_registered_data, sender_id, receiver_id)
    data = uri_of_registered_data + sender_id + receiver_id
    #data = 'uttam'
    hashed_data = _get_hash(data)
    print(hashed_data)
    re_hashed_data = _get_hash(hashed_data)
    print(re_hashed_data)
    signature = private_key_sender.sign(hashed_data)
    print('signed_data: ', signed_data)
    print('signature: ', signature)
    print('Is signed_data same as signature? ', signature == signed_data)
    signature_of_rehashed_data = private_key_sender.sign(re_hashed_data)
    print('signature_of_rehashed_data: ', signature_of_rehashed_data)










