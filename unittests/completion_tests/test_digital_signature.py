import os
from unittest import TestCase
from cryptography.hazmat.primitives.asymmetric import ed25519
from src.utils.digital_signature import DigitalSignature


class TestDigitalSignature(TestCase):
    def setUp(self) -> None:
        root = 'src'
        prefix = ''
        while not os.path.exists(f'{prefix}{root}'):
            prefix = f'../{prefix}'
        self.path_to_private_key = f'{prefix}src/keys/id_0_ed25519'
        self.path_to_public_key = f'{prefix}src/keys/id_0_ed25519.pub'
        with open(self.path_to_private_key, 'rb') as pem_in:
            pemlines = pem_in.read()
        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(pemlines)
        with open(self.path_to_public_key, 'rb') as pem_in:
            pemlines = pem_in.read()
        self.public_key = ed25519.Ed25519PublicKey.from_public_bytes(pemlines)

        self.own_digital_signature = DigitalSignature(self.public_key, self.private_key)

    def test_sign_data(self):
        try:
            data = b'my data'
            self.own_digital_signature.sign_data(data)
        except ValueError:
            self.fail('Exception raised')

    """
    def test_verify_signature(self):
        try:
            message = b'the  message'
            signature = self.private_key.sign(message)
            self.own_digital_signature.verify_signature(signature, message)
        except ValueError:
            self.fail('Exception raised')
    """