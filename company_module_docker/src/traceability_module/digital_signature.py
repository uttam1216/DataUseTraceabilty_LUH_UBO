import hashlib

from cryptography.exceptions import InvalidSignature

# function to return hash of the data being passed to this function as parameter
def _get_hash(data):
    # to be signed, the data must be of type bytes, list or tuple of integers. We do not deal with lists and our tuples
    # are not made of integers
    if isinstance(data, str):
        try:
            hash_data = eval(data)
        except:
            hash_data = str.encode(data)
        return hash_data

    if isinstance(data, bytes):
        hash_data = data
        """
        hash_data = hashlib.sha256()
        hash_data.update(hash_data)
        hash_data = hash_data.digest()
        """
        return hash_data
    # data of type tuple
    """
    1- hash the tuple / list using hash() function. this return an integer
    2- transform the hash into encoded string using str() and str.encode() functions:
        the reverse is eval() function to get the hash back
        The result of this transformation is of type bytes (main requirement to be able to sign a data)
    hashlib is used to hash bytes for simple cases like b'value' if we absolutely want to hash it
    - hash the bytes data using hashlib.sha256().update()
    - then get the digest which is of type bytes using digest() function
    """
    first_hash = hash(data)
    hash_data = str.encode(str(first_hash))
    return hash_data

# class to define function to sign the data
class DigitalSignature:
    def __init__(self, public_key, private_key=None):
        self.__private_key = private_key
        self.public_key = public_key

    # function to define teh process to sign the data
    def sign_data(self, data):
        try:
            if self.__private_key is None:
                raise ValueError("No private key available")
            # we put the case of tuples apart for a special treatment
            if isinstance(data, type("")) or isinstance(data, type(())):
                hash_data = _get_hash(data)
                signature = self.__private_key.sign(hash_data)
            else:
                signature = self.__private_key.sign(data)
            return signature
        except ValueError as e:
            return e.args[0]

    """
    def verify_signature(self, signature, hash_data):
        try:
            self.public_key.verify(signature, hash_data)
        except InvalidSignature as e:
            return e.args[0]
        return True
    """