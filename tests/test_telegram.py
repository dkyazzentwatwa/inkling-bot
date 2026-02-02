"""
Project Inkling - Telegram Tests

Tests for core/telegram.py - X25519 encrypted messaging.
"""

import os
import pytest
from pathlib import Path


class TestTelegramCrypto:
    """Tests for TelegramCrypto class."""

    def test_initialization(self, temp_data_dir):
        """Test TelegramCrypto initialization."""
        from core.telegram import TelegramCrypto

        crypto = TelegramCrypto(data_dir=temp_data_dir)
        crypto.initialize()

        # Key file should be created
        assert (Path(temp_data_dir) / "telegram_key.pem").exists()

        # Public key should be 32 bytes (64 hex chars) for X25519
        assert len(crypto.public_key_hex) == 64
        assert len(crypto.public_key_bytes) == 32

    def test_key_persistence(self, temp_data_dir):
        """Test that key persists across instances."""
        from core.telegram import TelegramCrypto

        # First initialization
        crypto1 = TelegramCrypto(data_dir=temp_data_dir)
        crypto1.initialize()
        key1 = crypto1.public_key_hex

        # Second initialization
        crypto2 = TelegramCrypto(data_dir=temp_data_dir)
        crypto2.initialize()
        key2 = crypto2.public_key_hex

        assert key1 == key2

    def test_encrypt_produces_output(self, telegram_crypto, second_telegram_crypto):
        """Test that encryption produces ciphertext and nonce."""
        plaintext = "Hello, secret message!"

        ciphertext, nonce = telegram_crypto.encrypt(
            plaintext, second_telegram_crypto.public_key_hex
        )

        assert len(ciphertext) > 0
        assert len(nonce) == 24  # 12 bytes = 24 hex chars

    def test_encrypt_decrypt_roundtrip(self, telegram_crypto, second_telegram_crypto):
        """Test that encrypted message can be decrypted."""
        original = "This is a secret message for testing!"

        # Encrypt with first crypto's private key, second crypto's public key
        ciphertext, nonce = telegram_crypto.encrypt(
            original, second_telegram_crypto.public_key_hex
        )

        # Decrypt with second crypto's private key, first crypto's public key
        decrypted = second_telegram_crypto.decrypt(
            ciphertext, nonce, telegram_crypto.public_key_hex
        )

        assert decrypted == original

    def test_encrypt_decrypt_with_unicode(self, telegram_crypto, second_telegram_crypto):
        """Test encryption with Unicode characters."""
        # Use valid Unicode (CJK characters and proper emoji)
        original = "Hello! \u4e16\u754c"  # Chinese for "world"

        ciphertext, nonce = telegram_crypto.encrypt(
            original, second_telegram_crypto.public_key_hex
        )

        decrypted = second_telegram_crypto.decrypt(
            ciphertext, nonce, telegram_crypto.public_key_hex
        )

        assert decrypted == original

    def test_encrypt_decrypt_empty_message(self, telegram_crypto, second_telegram_crypto):
        """Test encryption of empty message."""
        original = ""

        ciphertext, nonce = telegram_crypto.encrypt(
            original, second_telegram_crypto.public_key_hex
        )

        decrypted = second_telegram_crypto.decrypt(
            ciphertext, nonce, telegram_crypto.public_key_hex
        )

        assert decrypted == original

    def test_encrypt_decrypt_long_message(self, telegram_crypto, second_telegram_crypto):
        """Test encryption of long message."""
        original = "A" * 10000

        ciphertext, nonce = telegram_crypto.encrypt(
            original, second_telegram_crypto.public_key_hex
        )

        decrypted = second_telegram_crypto.decrypt(
            ciphertext, nonce, telegram_crypto.public_key_hex
        )

        assert decrypted == original

    def test_decrypt_with_wrong_key_fails(self, telegram_crypto, second_telegram_crypto, temp_data_dir):
        """Test that decryption with wrong key fails."""
        from core.telegram import TelegramCrypto

        # Create a third party
        third_dir = os.path.join(temp_data_dir, "device3")
        os.makedirs(third_dir, exist_ok=True)
        third_crypto = TelegramCrypto(data_dir=third_dir)
        third_crypto.initialize()

        # Encrypt from first to second
        original = "Secret message"
        ciphertext, nonce = telegram_crypto.encrypt(
            original, second_telegram_crypto.public_key_hex
        )

        # Third party tries to decrypt (should fail)
        with pytest.raises(ValueError, match="Decryption failed"):
            third_crypto.decrypt(
                ciphertext, nonce, telegram_crypto.public_key_hex
            )

    def test_decrypt_with_tampered_ciphertext(self, telegram_crypto, second_telegram_crypto):
        """Test that tampered ciphertext fails to decrypt."""
        original = "Secret message"
        ciphertext, nonce = telegram_crypto.encrypt(
            original, second_telegram_crypto.public_key_hex
        )

        # Tamper with ciphertext (change a character)
        import base64
        raw = base64.b64decode(ciphertext)
        tampered = base64.b64encode(bytes([raw[0] ^ 0xFF]) + raw[1:]).decode()

        with pytest.raises(ValueError, match="Decryption failed"):
            second_telegram_crypto.decrypt(
                tampered, nonce, telegram_crypto.public_key_hex
            )

    def test_decrypt_with_wrong_nonce(self, telegram_crypto, second_telegram_crypto):
        """Test that wrong nonce fails to decrypt."""
        original = "Secret message"
        ciphertext, nonce = telegram_crypto.encrypt(
            original, second_telegram_crypto.public_key_hex
        )

        # Use wrong nonce
        wrong_nonce = "00" * 12  # 12 zero bytes

        with pytest.raises(ValueError, match="Decryption failed"):
            second_telegram_crypto.decrypt(
                ciphertext, wrong_nonce, telegram_crypto.public_key_hex
            )

    def test_each_encryption_has_unique_nonce(self, telegram_crypto, second_telegram_crypto):
        """Test that each encryption produces a unique nonce."""
        plaintext = "Same message"

        _, nonce1 = telegram_crypto.encrypt(
            plaintext, second_telegram_crypto.public_key_hex
        )
        _, nonce2 = telegram_crypto.encrypt(
            plaintext, second_telegram_crypto.public_key_hex
        )

        assert nonce1 != nonce2


class TestTelegram:
    """Tests for Telegram dataclass."""

    def test_telegram_creation(self):
        """Test creating a Telegram object."""
        from core.telegram import Telegram

        telegram = Telegram(
            id="msg123",
            from_device_id="device456",
            from_public_key="pubkey789",
            content="Hello!",
            created_at="2024-01-01T00:00:00Z",
            is_delivered=False,
        )

        assert telegram.id == "msg123"
        assert telegram.from_device_id == "device456"
        assert telegram.content == "Hello!"
        assert telegram.is_delivered is False

    def test_telegram_to_dict(self):
        """Test Telegram serialization."""
        from core.telegram import Telegram

        telegram = Telegram(
            id="msg123",
            from_device_id="device456",
            from_public_key="pubkey789",
            content="Hello!",
            created_at="2024-01-01T00:00:00Z",
            is_delivered=True,
        )

        d = telegram.to_dict()

        assert d["id"] == "msg123"
        assert d["content"] == "Hello!"
        assert d["is_delivered"] is True


class TestTelegramManager:
    """Tests for TelegramManager class."""

    def test_inbox_initially_empty(self, telegram_crypto):
        """Test that inbox starts empty."""
        from core.telegram import TelegramManager

        # Mock API client
        class MockAPIClient:
            pass

        manager = TelegramManager(telegram_crypto, MockAPIClient())

        assert manager.inbox == []
        assert manager.unread_count == 0

    def test_unread_count(self, telegram_crypto):
        """Test unread message counting."""
        from core.telegram import TelegramManager, Telegram

        class MockAPIClient:
            pass

        manager = TelegramManager(telegram_crypto, MockAPIClient())

        # Manually set inbox with mixed delivery status
        manager._inbox = [
            Telegram("1", "dev1", "key1", "msg1", "2024-01-01", is_delivered=False),
            Telegram("2", "dev2", "key2", "msg2", "2024-01-01", is_delivered=True),
            Telegram("3", "dev3", "key3", "msg3", "2024-01-01", is_delivered=False),
        ]

        assert manager.unread_count == 2
