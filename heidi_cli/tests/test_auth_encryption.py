import unittest
from unittest.mock import patch, MagicMock
from heidi_cli.auth_encryption import encrypt_token, decrypt_token, get_encryption_key
from cryptography.fernet import Fernet

class TestAuthEncryption(unittest.TestCase):

    def setUp(self):
        # Generate a real Fernet key so that encryption actually works with the mocked key getter
        self.key = Fernet.generate_key()

        # Patch the get_encryption_key function where it is defined
        self.patcher = patch('heidi_cli.auth_encryption.get_encryption_key')
        self.mock_get_key = self.patcher.start()
        self.mock_get_key.return_value = self.key

    def tearDown(self):
        self.patcher.stop()

    def test_encrypt_token_empty(self):
        """Test encrypt_token with empty inputs."""
        self.assertEqual(encrypt_token(""), "")
        self.assertEqual(encrypt_token(None), "")

    def test_encrypt_token_valid(self):
        """Test encrypt_token with valid input."""
        token = "test_token"
        encrypted = encrypt_token(token)

        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, token)
        self.assertNotEqual(encrypted, "")

        # Verify it's decryptable with the same key
        f = Fernet(self.key)
        decrypted = f.decrypt(encrypted.encode()).decode()
        self.assertEqual(decrypted, token)

    def test_decrypt_token_empty(self):
        """Test decrypt_token with empty inputs."""
        self.assertIsNone(decrypt_token(""))
        self.assertIsNone(decrypt_token(None))

    def test_decrypt_token_invalid(self):
        """Test decrypt_token with invalid/corrupted input."""
        # This should return None as the exception is caught
        self.assertIsNone(decrypt_token("invalid_token_string"))

    def test_roundtrip(self):
        """Test that encryption followed by decryption returns the original token."""
        token = "secret_token_123"
        encrypted = encrypt_token(token)
        decrypted = decrypt_token(encrypted)
        self.assertEqual(decrypted, token)

    def test_encryption_key_mocked(self):
        """Verify that get_encryption_key is called during encryption."""
        encrypt_token("test")
        self.mock_get_key.assert_called()
