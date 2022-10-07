import os
from unittest import TestCase
from cryptography.hazmat.primitives.asymmetric import ed25519
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

    def test_generate_private_key(self):
        try:
            em.generate_private_key()
        except ValueError:
            self.fail('Exception raised')

    def test_generate_public_key(self):
        try:
            em.generate_public_key(ed25519.Ed25519PrivateKey.generate())
        except ValueError:
            self.fail('Exception raised')

    def test_save_private_key(self):
        try:
            n = 0
            path_to_private_key = f'{self.path_to_private_keys}/{self.private_key_filenames[n]}'
            em.save_private_key(ed25519.Ed25519PrivateKey.generate(), path_to_private_key)
        except ValueError:
            self.fail('Exception raised')

    def test_save_public_key(self):
        try:
            n = 0
            path_to_public_key = f'{self.path_to_public_keys}/{self.public_key_filenames[n]}'
            em.save_public_key(ed25519.Ed25519PrivateKey.generate().public_key(), path_to_public_key)
        except ValueError:
            self.fail('Exception raised')

    def test_load_private_key(self):
        try:
            n = 0
            path_to_private_key = f'{self.path_to_private_keys}/{self.private_key_filenames[n]}'
            em.load_private_key(path_to_private_key)
        except ValueError:
            self.fail('Exception raised')

    def test_load_public_key(self):
        try:
            n = 0
            path_to_public_key = f'{self.path_to_public_keys}/{self.public_key_filenames[n]}'
            em.load_public_key(path_to_public_key)
        except ValueError:
            self.fail('Exception raised')
