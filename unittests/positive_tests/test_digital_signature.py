import os
from unittest import TestCase

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from src.utils.digital_signature import DigitalSignature
from src.utils import encryption_module as em


class TestDigitalSignature(TestCase):
    def setUp(self) -> None:
        self.private_key = em.generate_private_key()
        self.public_key = em.generate_public_key(self.private_key)

        self.own_digital_signature = DigitalSignature(public_key=self.public_key, private_key=self.private_key)

    def test_sign_data(self):
        data = b'my data'
        direct_signature = self.private_key.sign(data)
        result_signature = self.own_digital_signature.sign_data(data)
        self.assertEqual(direct_signature, result_signature)

    """
    def test_verify_signature(self):
        message = b'the  message'
        signature = self.private_key.sign(message)

        self.assertTrue(self.own_digital_signature.verify_signature(signature, message))
    """