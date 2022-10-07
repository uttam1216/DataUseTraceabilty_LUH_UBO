import os
from unittest import TestCase
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from src.utils import encryption_module as em


class Test(TestCase):
    def setUp(self) -> None:
        root = 'src'
        prefix = ''
        while not os.path.exists(f'{prefix}{root}'):
            prefix = f'../{prefix}'
        self.path_to_private_keys = f'{prefix}src/keys'
        self.path_to_public_keys = f'{prefix}src/keys'
        self.uniform_resource_identifiers = []
        self.private_key_filenames = []
        self.public_key_filenames = []

        n = 6
        for i in range(n):
            identifier = f'id_{i}'
            self.uniform_resource_identifiers.append(identifier)
            self.private_key_filenames.append(f'{identifier}_ed25519')
            self.public_key_filenames.append(f'{identifier}_ed25519.pub')
        self.private_key = em.generate_private_key()
        self.public_key = em.generate_public_key(self.private_key)

    def test_generate_private_key(self):
        self.assertTrue(isinstance(self.private_key, Ed25519PrivateKey))

    def test_generate_public_key(self):
        self.assertTrue(isinstance(self.public_key, Ed25519PublicKey))

    def test_save_and_load_private_key(self):
        n = 0
        path_to_private_key = f'{self.path_to_private_keys}/{self.private_key_filenames[n]}'
        em.save_private_key(self.private_key, path_to_private_key)
        loaded_private_key = em.load_private_key(path_to_private_key)
        data = b'my data'
        signature_original_key = self.private_key.sign(data)
        signature_loaded_key = loaded_private_key.sign(data)

        self.assertEqual(signature_original_key, signature_loaded_key)

    def test_save_and_load_public_key(self):
        n = 0
        path_to_public_key = f'{self.path_to_public_keys}/{self.public_key_filenames[n]}'
        em.save_public_key(self.public_key, path_to_public_key)
        loaded_public_key = em.load_public_key(path_to_public_key)
        data = b'my data'
        signature_original_key = self.private_key.sign(data)
        self.assertIsNone(loaded_public_key.verify(signature_original_key, data))

