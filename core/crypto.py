"""
Project Inkling - Cryptographic Identity (DNA)

Handles device identity using Ed25519 signatures and hardware fingerprinting.
Implements challenge-response authentication for the Conservatory social network.
"""

import os
import hashlib
import time
import json
import re
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.backends import default_backend


class Identity:
    """
    Device identity manager using Ed25519 keys and hardware fingerprinting.

    The "DNA" consists of:
    - Ed25519 keypair (stored in identity.pem)
    - Hardware hash (CPU serial + primary MAC address)

    Together these provide proof that messages come from a physical device.
    """

    def __init__(self, data_dir: str = "~/.inkling"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.key_path = self.data_dir / "identity.pem"
        self._private_key: Optional[Ed25519PrivateKey] = None
        self._public_key: Optional[Ed25519PublicKey] = None
        self._hardware_hash: Optional[str] = None

    def initialize(self) -> None:
        """Load existing identity or generate a new one."""
        if self.key_path.exists():
            self._load_key()
        else:
            self._generate_key()

        self._hardware_hash = self._compute_hardware_hash()

    def _generate_key(self) -> None:
        """Generate a new Ed25519 keypair."""
        self._private_key = Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

        # Save private key to file
        pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        self.key_path.write_bytes(pem)
        os.chmod(self.key_path, 0o600)  # Restrict permissions

    def _load_key(self) -> None:
        """Load existing keypair from file."""
        pem = self.key_path.read_bytes()
        self._private_key = serialization.load_pem_private_key(
            pem,
            password=None,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

    def _compute_hardware_hash(self) -> str:
        """
        Compute hardware fingerprint from CPU serial and MAC address.

        On Raspberry Pi, reads from /proc/cpuinfo.
        Falls back to a stable machine-specific ID on other platforms.
        """
        cpu_serial = self._get_cpu_serial()
        mac_address = self._get_mac_address()

        # Combine and hash
        combined = f"{cpu_serial}:{mac_address}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def _get_cpu_serial(self) -> str:
        """Get CPU serial number (Pi) or fallback identifier."""
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("Serial"):
                        return line.split(":")[1].strip()
        except (FileNotFoundError, IndexError):
            pass

        # Fallback: use machine-id on Linux or hostname elsewhere
        try:
            return Path("/etc/machine-id").read_text().strip()
        except FileNotFoundError:
            import socket
            return hashlib.sha256(socket.gethostname().encode()).hexdigest()[:16]

    def _get_mac_address(self) -> str:
        """Get primary network interface MAC address."""
        import uuid
        # uuid.getnode() returns MAC as integer
        mac = uuid.getnode()
        return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(40, -1, -8))

    @property
    def public_key_bytes(self) -> bytes:
        """Get public key as raw bytes (32 bytes for Ed25519)."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    @property
    def public_key_hex(self) -> str:
        """Get public key as hex string."""
        return self.public_key_bytes.hex()

    @property
    def hardware_hash(self) -> str:
        """Get hardware fingerprint hash."""
        return self._hardware_hash

    def sign(self, message: bytes) -> bytes:
        """Sign a message with the device's private key."""
        return self._private_key.sign(message)

    def sign_payload(self, payload: dict, nonce: Optional[str] = None) -> dict:
        """
        Sign a JSON payload for API submission.

        Args:
            payload: The data to sign
            nonce: Optional server-provided challenge nonce

        Returns:
            Dict with payload, signature, public_key, hardware_hash, and timestamp
        """
        timestamp = int(time.time())

        # Create signing material
        sign_data = {
            "payload": payload,
            "timestamp": timestamp,
            "hardware_hash": self._hardware_hash,
        }
        if nonce:
            sign_data["nonce"] = nonce

        sign_bytes = json.dumps(sign_data, sort_keys=True).encode()
        signature = self.sign(sign_bytes)

        return {
            "payload": payload,
            "timestamp": timestamp,
            "hardware_hash": self._hardware_hash,
            "public_key": self.public_key_hex,
            "signature": signature.hex(),
            "nonce": nonce,
        }

    @staticmethod
    def verify_signature(
        public_key_hex: str,
        signature_hex: str,
        payload: dict,
        timestamp: int,
        hardware_hash: str,
        nonce: Optional[str] = None,
        max_age_seconds: int = 300
    ) -> bool:
        """
        Verify a signed payload.

        Args:
            public_key_hex: Signer's public key as hex
            signature_hex: Signature as hex
            payload: The original payload
            timestamp: Unix timestamp from signature
            hardware_hash: Hardware fingerprint
            nonce: Server challenge nonce if used
            max_age_seconds: Maximum age of signature to accept

        Returns:
            True if signature is valid and recent
        """
        # Check timestamp freshness
        now = int(time.time())
        if abs(now - timestamp) > max_age_seconds:
            return False

        # Reconstruct signing material
        sign_data = {
            "payload": payload,
            "timestamp": timestamp,
            "hardware_hash": hardware_hash,
        }
        if nonce:
            sign_data["nonce"] = nonce

        sign_bytes = json.dumps(sign_data, sort_keys=True).encode()

        # Load public key and verify
        try:
            public_key_bytes = bytes.fromhex(public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            signature = bytes.fromhex(signature_hex)

            public_key.verify(signature, sign_bytes)
            return True
        except Exception:
            return False

    def get_device_info(self) -> dict:
        """Get device identity information for registration."""
        return {
            "public_key": self.public_key_hex,
            "hardware_hash": self._hardware_hash,
        }


# Challenge-response utilities for server authentication
def generate_nonce() -> str:
    """Generate a random 32-byte nonce for challenge-response."""
    return os.urandom(32).hex()


def verify_challenge_response(
    public_key_hex: str,
    hardware_hash: str,
    nonce: str,
    response_signature_hex: str
) -> bool:
    """
    Verify a challenge-response from a device.

    The device must sign: nonce + hardware_hash
    """
    try:
        public_key_bytes = bytes.fromhex(public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)

        challenge_data = f"{nonce}:{hardware_hash}".encode()
        signature = bytes.fromhex(response_signature_hex)

        public_key.verify(signature, challenge_data)
        return True
    except Exception:
        return False
