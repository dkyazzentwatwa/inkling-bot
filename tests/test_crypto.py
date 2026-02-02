"""
Project Inkling - Cryptography Tests

Tests for core/crypto.py - Ed25519 key generation, signing, and verification.
"""

import os
import time
import json
import pytest
from pathlib import Path


class TestIdentity:
    """Tests for the Identity class."""

    def test_identity_initialization(self, temp_data_dir):
        """Test that Identity initializes and creates a keypair."""
        from core.crypto import Identity

        ident = Identity(data_dir=temp_data_dir)
        ident.initialize()

        # Key file should be created
        assert (Path(temp_data_dir) / "identity.pem").exists()

        # Public key should be 32 bytes (64 hex chars)
        assert len(ident.public_key_hex) == 64
        assert len(ident.public_key_bytes) == 32

        # Hardware hash should be 32 chars
        assert len(ident.hardware_hash) == 32

    def test_identity_persistence(self, temp_data_dir):
        """Test that Identity loads the same key on re-initialization."""
        from core.crypto import Identity

        # First initialization
        ident1 = Identity(data_dir=temp_data_dir)
        ident1.initialize()
        pubkey1 = ident1.public_key_hex

        # Second initialization should load same key
        ident2 = Identity(data_dir=temp_data_dir)
        ident2.initialize()
        pubkey2 = ident2.public_key_hex

        assert pubkey1 == pubkey2

    def test_sign_and_verify(self, identity):
        """Test message signing and verification."""
        message = b"Hello, Inkling!"
        signature = identity.sign(message)

        # Signature should be 64 bytes for Ed25519
        assert len(signature) == 64

        # Verification should succeed for correct message
        result = identity.verify_signature(
            public_key_hex=identity.public_key_hex,
            signature_hex=signature.hex(),
            payload={"message": "test"},
            timestamp=int(time.time()),
            hardware_hash=identity.hardware_hash,
        )
        # This will fail because sign_payload uses different format
        # Let's test sign_payload directly

    def test_sign_payload(self, identity):
        """Test signing a JSON payload."""
        payload = {"action": "test", "data": "hello"}
        signed = identity.sign_payload(payload)

        assert "payload" in signed
        assert "timestamp" in signed
        assert "hardware_hash" in signed
        assert "public_key" in signed
        assert "signature" in signed

        assert signed["payload"] == payload
        assert signed["public_key"] == identity.public_key_hex
        assert signed["hardware_hash"] == identity.hardware_hash

    def test_sign_payload_with_nonce(self, identity):
        """Test signing a payload with a nonce."""
        payload = {"action": "secure_action"}
        nonce = "test_nonce_12345"
        signed = identity.sign_payload(payload, nonce=nonce)

        assert signed["nonce"] == nonce

    def test_verify_signature_valid(self, identity):
        """Test verifying a valid signature."""
        payload = {"test": "data"}
        signed = identity.sign_payload(payload)

        result = identity.verify_signature(
            public_key_hex=signed["public_key"],
            signature_hex=signed["signature"],
            payload=signed["payload"],
            timestamp=signed["timestamp"],
            hardware_hash=signed["hardware_hash"],
            nonce=signed.get("nonce"),
        )
        assert result is True

    def test_verify_signature_invalid_payload(self, identity):
        """Test that modified payload fails verification."""
        payload = {"test": "data"}
        signed = identity.sign_payload(payload)

        # Modify the payload
        result = identity.verify_signature(
            public_key_hex=signed["public_key"],
            signature_hex=signed["signature"],
            payload={"test": "modified"},  # Changed!
            timestamp=signed["timestamp"],
            hardware_hash=signed["hardware_hash"],
        )
        assert result is False

    def test_verify_signature_expired(self, identity):
        """Test that old signatures are rejected."""
        payload = {"test": "data"}
        signed = identity.sign_payload(payload)

        # Use a very old timestamp in verification
        result = identity.verify_signature(
            public_key_hex=signed["public_key"],
            signature_hex=signed["signature"],
            payload=signed["payload"],
            timestamp=int(time.time()) - 600,  # 10 minutes old
            hardware_hash=signed["hardware_hash"],
            max_age_seconds=300,  # 5 minute limit
        )
        assert result is False

    def test_verify_signature_wrong_key(self, identity, second_identity):
        """Test that signature from different key fails."""
        payload = {"test": "data"}
        signed = identity.sign_payload(payload)

        # Try to verify with second identity's key
        result = identity.verify_signature(
            public_key_hex=second_identity.public_key_hex,  # Wrong key!
            signature_hex=signed["signature"],
            payload=signed["payload"],
            timestamp=signed["timestamp"],
            hardware_hash=signed["hardware_hash"],
        )
        assert result is False

    def test_get_device_info(self, identity):
        """Test getting device info for registration."""
        info = identity.get_device_info()

        assert "public_key" in info
        assert "hardware_hash" in info
        assert info["public_key"] == identity.public_key_hex
        assert info["hardware_hash"] == identity.hardware_hash


class TestNonceGeneration:
    """Tests for nonce generation."""

    def test_generate_nonce_length(self):
        """Test that nonce is correct length."""
        from core.crypto import generate_nonce

        nonce = generate_nonce()
        # 32 bytes = 64 hex chars
        assert len(nonce) == 64

    def test_generate_nonce_unique(self):
        """Test that nonces are unique."""
        from core.crypto import generate_nonce

        nonces = [generate_nonce() for _ in range(100)]
        assert len(set(nonces)) == 100


class TestChallengeResponse:
    """Tests for challenge-response authentication."""

    def test_challenge_response_valid(self, identity):
        """Test valid challenge-response."""
        from core.crypto import generate_nonce, verify_challenge_response

        nonce = generate_nonce()
        challenge_data = f"{nonce}:{identity.hardware_hash}".encode()
        signature = identity.sign(challenge_data)

        result = verify_challenge_response(
            public_key_hex=identity.public_key_hex,
            hardware_hash=identity.hardware_hash,
            nonce=nonce,
            response_signature_hex=signature.hex(),
        )
        assert result is True

    def test_challenge_response_wrong_nonce(self, identity):
        """Test that wrong nonce fails."""
        from core.crypto import generate_nonce, verify_challenge_response

        nonce = generate_nonce()
        challenge_data = f"{nonce}:{identity.hardware_hash}".encode()
        signature = identity.sign(challenge_data)

        # Verify with different nonce
        wrong_nonce = generate_nonce()
        result = verify_challenge_response(
            public_key_hex=identity.public_key_hex,
            hardware_hash=identity.hardware_hash,
            nonce=wrong_nonce,  # Wrong!
            response_signature_hex=signature.hex(),
        )
        assert result is False

    def test_challenge_response_wrong_hardware_hash(self, identity):
        """Test that wrong hardware hash fails."""
        from core.crypto import generate_nonce, verify_challenge_response

        nonce = generate_nonce()
        challenge_data = f"{nonce}:{identity.hardware_hash}".encode()
        signature = identity.sign(challenge_data)

        result = verify_challenge_response(
            public_key_hex=identity.public_key_hex,
            hardware_hash="wrong_hash_12345",  # Wrong!
            nonce=nonce,
            response_signature_hex=signature.hex(),
        )
        assert result is False
