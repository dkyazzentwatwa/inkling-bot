"""
Project Inkling - Telegram (Encrypted DMs)

End-to-end encrypted messages between Inklings using X25519 key exchange.
"""

import os
import json
import base64
from typing import Optional, Tuple
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class TelegramCrypto:
    """
    Handles encryption for telegrams (private messages between devices).

    Uses X25519 for key exchange and ChaCha20-Poly1305 for symmetric encryption.
    Each device has a persistent X25519 keypair separate from their Ed25519 signing key.
    """

    def __init__(self, data_dir: str = "~/.inkling"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.key_path = self.data_dir / "telegram_key.pem"
        self._private_key: Optional[X25519PrivateKey] = None
        self._public_key: Optional[X25519PublicKey] = None

    def initialize(self) -> None:
        """Load existing encryption key or generate a new one."""
        if self.key_path.exists():
            self._load_key()
        else:
            self._generate_key()

    def _generate_key(self) -> None:
        """Generate a new X25519 keypair for encryption."""
        self._private_key = X25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

        # Save private key
        pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.key_path.write_bytes(pem)
        os.chmod(self.key_path, 0o600)

    def _load_key(self) -> None:
        """Load existing keypair from file."""
        pem = self.key_path.read_bytes()
        self._private_key = serialization.load_pem_private_key(pem, password=None)
        self._public_key = self._private_key.public_key()

    @property
    def public_key_bytes(self) -> bytes:
        """Get public key as raw bytes (32 bytes for X25519)."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    @property
    def public_key_hex(self) -> str:
        """Get public key as hex string."""
        return self.public_key_bytes.hex()

    def _derive_shared_key(self, peer_public_key_bytes: bytes) -> bytes:
        """Derive a shared symmetric key using X25519 + HKDF."""
        peer_public_key = X25519PublicKey.from_public_bytes(peer_public_key_bytes)

        # Perform X25519 key exchange
        shared_secret = self._private_key.exchange(peer_public_key)

        # Derive symmetric key using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"inkling-telegram-v1",
        )
        return hkdf.derive(shared_secret)

    def encrypt(self, plaintext: str, recipient_public_key_hex: str) -> Tuple[str, str]:
        """
        Encrypt a message for a recipient.

        Args:
            plaintext: Message to encrypt
            recipient_public_key_hex: Recipient's X25519 public key as hex

        Returns:
            Tuple of (encrypted_content_base64, nonce_hex)
        """
        # Derive shared key
        recipient_public_key = bytes.fromhex(recipient_public_key_hex)
        shared_key = self._derive_shared_key(recipient_public_key)

        # Generate random nonce
        nonce = os.urandom(12)

        # Encrypt with ChaCha20-Poly1305
        cipher = ChaCha20Poly1305(shared_key)
        ciphertext = cipher.encrypt(nonce, plaintext.encode(), None)

        return base64.b64encode(ciphertext).decode(), nonce.hex()

    def decrypt(self, encrypted_content_base64: str, nonce_hex: str, sender_public_key_hex: str) -> str:
        """
        Decrypt a message from a sender.

        Args:
            encrypted_content_base64: Encrypted content as base64
            nonce_hex: Encryption nonce as hex
            sender_public_key_hex: Sender's X25519 public key as hex

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (wrong key or tampered)
        """
        # Derive shared key (same as sender derived)
        sender_public_key = bytes.fromhex(sender_public_key_hex)
        shared_key = self._derive_shared_key(sender_public_key)

        # Decrypt
        nonce = bytes.fromhex(nonce_hex)
        ciphertext = base64.b64decode(encrypted_content_base64)

        cipher = ChaCha20Poly1305(shared_key)
        try:
            plaintext = cipher.decrypt(nonce, ciphertext, None)
            return plaintext.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


class Telegram:
    """A telegram message (encrypted DM)."""

    def __init__(
        self,
        id: str,
        from_device_id: str,
        from_public_key: str,  # X25519 encryption key
        content: str,  # Decrypted content
        created_at: str,
        is_delivered: bool = False,
    ):
        self.id = id
        self.from_device_id = from_device_id
        self.from_public_key = from_public_key
        self.content = content
        self.created_at = created_at
        self.is_delivered = is_delivered

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_device_id": self.from_device_id,
            "from_public_key": self.from_public_key,
            "content": self.content,
            "created_at": self.created_at,
            "is_delivered": self.is_delivered,
        }


class TelegramManager:
    """
    Manages sending and receiving encrypted telegrams.

    Works with the API client to:
    - Send encrypted messages to other devices
    - Fetch and decrypt incoming messages
    - Track local inbox
    """

    def __init__(self, crypto: TelegramCrypto, api_client):
        self.crypto = crypto
        self.api_client = api_client
        self._inbox: list = []

    async def send(
        self,
        recipient_public_key: str,  # Ed25519 signing key (device ID)
        recipient_encryption_key: str,  # X25519 encryption key
        message: str,
    ) -> dict:
        """
        Send an encrypted telegram to another device.

        Args:
            recipient_public_key: Recipient's Ed25519 public key (device ID)
            recipient_encryption_key: Recipient's X25519 public key
            message: Plaintext message

        Returns:
            API response
        """
        # Encrypt the message
        encrypted_content, nonce = self.crypto.encrypt(message, recipient_encryption_key)

        # Send via API
        return await self.api_client.send_telegram(
            to_public_key=recipient_public_key,
            encrypted_content=encrypted_content,
            content_nonce=nonce,
            sender_encryption_key=self.crypto.public_key_hex,
        )

    async def check_inbox(self) -> list:
        """
        Check for new telegrams and decrypt them.

        Returns:
            List of decrypted Telegram objects
        """
        # Fetch encrypted telegrams from API
        encrypted_telegrams = await self.api_client.get_telegrams()

        telegrams = []
        for t in encrypted_telegrams:
            try:
                # Decrypt content
                content = self.crypto.decrypt(
                    encrypted_content_base64=t["encrypted_content"],
                    nonce_hex=t["content_nonce"],
                    sender_public_key_hex=t["sender_encryption_key"],
                )

                telegram = Telegram(
                    id=t["id"],
                    from_device_id=t["from_device_id"],
                    from_public_key=t["sender_encryption_key"],
                    content=content,
                    created_at=t["created_at"],
                    is_delivered=t.get("is_delivered", False),
                )
                telegrams.append(telegram)

            except ValueError as e:
                # Decryption failed - skip this message
                print(f"[Telegram] Failed to decrypt: {e}")
                continue

        self._inbox = telegrams
        return telegrams

    @property
    def inbox(self) -> list:
        """Get cached inbox."""
        return self._inbox

    @property
    def unread_count(self) -> int:
        """Count unread telegrams."""
        return len([t for t in self._inbox if not t.is_delivered])
