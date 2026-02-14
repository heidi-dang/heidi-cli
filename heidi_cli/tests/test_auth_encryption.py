import sys
from unittest.mock import MagicMock

# Mock missing dependencies before they are imported by heidi_cli.config
sys.modules["keyring"] = MagicMock()

import pytest
from heidi_cli.auth_encryption import (
    encrypt_token,
    decrypt_token,
    generate_state,
    generate_code_verifier,
    generate_code_challenge,
)

class TestAuthEncryption:
    def test_encrypt_decrypt_roundtrip(self, tmp_path, monkeypatch):
        # Mock HEIDI_HOME to use tmp_path for the encryption key
        monkeypatch.setenv("HEIDI_HOME", str(tmp_path))

        token = "test_token_123"
        encrypted = encrypt_token(token)
        assert encrypted != token
        assert encrypted != ""

        decrypted = decrypt_token(encrypted)
        assert decrypted == token

    def test_decrypt_none_or_empty(self):
        assert decrypt_token(None) is None
        assert decrypt_token("") is None

    def test_decrypt_invalid_token(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HEIDI_HOME", str(tmp_path))
        # Random string that is not a valid Fernet token
        assert decrypt_token("invalid_token") is None

    def test_encrypt_none_or_empty(self):
        # encrypt_token(None) should return "" based on implementation:
        # if not token: return ""
        assert encrypt_token(None) == ""
        assert encrypt_token("") == ""

    def test_generate_state(self):
        state = generate_state()
        assert isinstance(state, str)
        assert len(state) > 0
        # Should be different each time
        assert generate_state() != state

    def test_generate_code_verifier(self):
        verifier = generate_code_verifier()
        assert isinstance(verifier, str)
        assert len(verifier) > 0
        assert generate_code_verifier() != verifier

    def test_generate_code_challenge(self):
        verifier = "test_verifier"
        challenge = generate_code_challenge(verifier)
        assert isinstance(challenge, str)
        assert len(challenge) > 0
        # deterministic
        assert generate_code_challenge(verifier) == challenge
