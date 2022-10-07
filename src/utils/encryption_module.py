from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# the following function generates the private key and returns it to the calling function
def generate_private_key():
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key

# the following function generates the public key for a provided private key and then returns it to the calling function
def generate_public_key(private_key):
    public_key = private_key.public_key()
    return public_key

# the following function saves the private key
def save_private_key(private_key, path_to_private_key):
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(path_to_private_key, 'wb') as pem_out:
        pem_out.write(pem)

# function to save the public key
def save_public_key(public_key, path_to_public_key):
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    with open(path_to_public_key, 'wb') as pem_out:
        pem_out.write(pem)

# function to load the private key
def load_private_key(path_to_private_key):
    with open(path_to_private_key, 'rb') as pem_in:
        pemlines = pem_in.read()
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(pemlines)
    return private_key

# function to load the public key
def load_public_key(path_to_public_key):
    with open(path_to_public_key, 'rb') as pem_in:
        pemlines = pem_in.read()
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(pemlines)
    return public_key
