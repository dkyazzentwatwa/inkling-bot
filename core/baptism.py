"""
Project Inkling - Baptism System (Web of Trust)

Device verification through trusted peer endorsement.
A device becomes "verified" when endorsed by existing verified devices.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class BaptismStatus(Enum):
    """Baptism/verification status."""
    UNBAPTIZED = "unbaptized"
    PENDING = "pending"  # Has requested baptism
    BAPTIZED = "baptized"  # Verified by trusted peers
    REVOKED = "revoked"  # Verification revoked


@dataclass
class BaptismRequest:
    """A request for baptism from an unbaptized device."""
    requester_public_key: str
    requester_name: str
    requester_hardware_hash: str
    message: str  # Why they want to be baptized
    created_at: str
    signature: str

    def to_dict(self) -> dict:
        return {
            "requester_public_key": self.requester_public_key,
            "requester_name": self.requester_name,
            "requester_hardware_hash": self.requester_hardware_hash,
            "message": self.message,
            "created_at": self.created_at,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaptismRequest":
        return cls(
            requester_public_key=data["requester_public_key"],
            requester_name=data["requester_name"],
            requester_hardware_hash=data["requester_hardware_hash"],
            message=data.get("message", ""),
            created_at=data["created_at"],
            signature=data["signature"],
        )


@dataclass
class BaptismEndorsement:
    """An endorsement from a verified device."""
    endorser_public_key: str
    endorser_name: str
    endorsed_public_key: str
    endorsed_name: str
    message: str  # Endorsement message
    created_at: str
    signature: str
    endorser_trust_level: int = 1  # Higher = more trusted

    def to_dict(self) -> dict:
        return {
            "endorser_public_key": self.endorser_public_key,
            "endorser_name": self.endorser_name,
            "endorsed_public_key": self.endorsed_public_key,
            "endorsed_name": self.endorsed_name,
            "message": self.message,
            "created_at": self.created_at,
            "signature": self.signature,
            "endorser_trust_level": self.endorser_trust_level,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaptismEndorsement":
        return cls(
            endorser_public_key=data["endorser_public_key"],
            endorser_name=data["endorser_name"],
            endorsed_public_key=data["endorsed_public_key"],
            endorsed_name=data["endorsed_name"],
            message=data.get("message", ""),
            created_at=data["created_at"],
            signature=data["signature"],
            endorser_trust_level=data.get("endorser_trust_level", 1),
        )


@dataclass
class TrustChain:
    """The chain of endorsements leading to a device's verification."""
    device_public_key: str
    device_name: str
    endorsements: List[BaptismEndorsement] = field(default_factory=list)
    status: BaptismStatus = BaptismStatus.UNBAPTIZED
    baptism_date: Optional[str] = None
    trust_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "device_public_key": self.device_public_key,
            "device_name": self.device_name,
            "endorsements": [e.to_dict() for e in self.endorsements],
            "status": self.status.value,
            "baptism_date": self.baptism_date,
            "trust_score": self.trust_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrustChain":
        return cls(
            device_public_key=data["device_public_key"],
            device_name=data["device_name"],
            endorsements=[BaptismEndorsement.from_dict(e) for e in data.get("endorsements", [])],
            status=BaptismStatus(data.get("status", "unbaptized")),
            baptism_date=data.get("baptism_date"),
            trust_score=data.get("trust_score", 0.0),
        )


class BaptismSystem:
    """
    Manages the web of trust for device verification.

    Rules:
    - First N devices are "genesis" devices (auto-verified by admin)
    - Other devices need endorsements from verified devices
    - Required endorsements decreases with endorser trust level
    - Verified status can be revoked
    """

    # Trust thresholds
    MIN_ENDORSEMENTS = 2  # Minimum endorsements needed
    TRUST_THRESHOLD = 3.0  # Total trust score needed for baptism

    @staticmethod
    def calculate_trust_score(endorsements: List[BaptismEndorsement]) -> float:
        """
        Calculate total trust score from endorsements.

        Higher trust level endorsers contribute more.
        """
        if not endorsements:
            return 0.0

        # Sum of endorser trust levels with diminishing returns
        score = 0.0
        for i, endorsement in enumerate(sorted(
            endorsements,
            key=lambda e: e.endorser_trust_level,
            reverse=True
        )):
            # First endorsement counts full, subsequent have diminishing value
            multiplier = 1.0 / (1 + i * 0.3)
            score += endorsement.endorser_trust_level * multiplier

        return score

    @staticmethod
    def check_baptism_eligibility(
        endorsements: List[BaptismEndorsement],
        min_endorsements: int = MIN_ENDORSEMENTS,
        trust_threshold: float = TRUST_THRESHOLD,
    ) -> tuple:
        """
        Check if a device is eligible for baptism.

        Returns:
            Tuple of (is_eligible, trust_score, reason)
        """
        if len(endorsements) < min_endorsements:
            return (
                False,
                0.0,
                f"Need {min_endorsements - len(endorsements)} more endorsements"
            )

        trust_score = BaptismSystem.calculate_trust_score(endorsements)

        if trust_score < trust_threshold:
            return (
                False,
                trust_score,
                f"Trust score {trust_score:.1f} below threshold {trust_threshold}"
            )

        return (True, trust_score, "Eligible for baptism")

    @staticmethod
    def create_baptism_request(
        identity,  # Identity object
        device_name: str,
        message: str = "",
    ) -> BaptismRequest:
        """Create a baptism request."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        request_data = {
            "requester_public_key": identity.public_key_hex,
            "requester_name": device_name,
            "requester_hardware_hash": identity.hardware_hash,
            "message": message,
            "created_at": timestamp,
        }

        sign_bytes = json.dumps(request_data, sort_keys=True).encode()
        signature = identity.sign(sign_bytes).hex()

        return BaptismRequest(
            requester_public_key=identity.public_key_hex,
            requester_name=device_name,
            requester_hardware_hash=identity.hardware_hash,
            message=message,
            created_at=timestamp,
            signature=signature,
        )

    @staticmethod
    def create_endorsement(
        identity,  # Endorser's Identity object
        endorser_name: str,
        endorsed_public_key: str,
        endorsed_name: str,
        message: str = "",
        trust_level: int = 1,
    ) -> BaptismEndorsement:
        """Create an endorsement for another device."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        endorsement_data = {
            "endorser_public_key": identity.public_key_hex,
            "endorser_name": endorser_name,
            "endorsed_public_key": endorsed_public_key,
            "endorsed_name": endorsed_name,
            "message": message,
            "created_at": timestamp,
            "endorser_trust_level": trust_level,
        }

        sign_bytes = json.dumps(endorsement_data, sort_keys=True).encode()
        signature = identity.sign(sign_bytes).hex()

        return BaptismEndorsement(
            endorser_public_key=identity.public_key_hex,
            endorser_name=endorser_name,
            endorsed_public_key=endorsed_public_key,
            endorsed_name=endorsed_name,
            message=message,
            created_at=timestamp,
            signature=signature,
            endorser_trust_level=trust_level,
        )

    @staticmethod
    def verify_endorsement_signature(
        endorsement: BaptismEndorsement,
    ) -> bool:
        """Verify an endorsement's signature."""
        from .crypto import Identity

        endorsement_data = {
            "endorser_public_key": endorsement.endorser_public_key,
            "endorser_name": endorsement.endorser_name,
            "endorsed_public_key": endorsement.endorsed_public_key,
            "endorsed_name": endorsement.endorsed_name,
            "message": endorsement.message,
            "created_at": endorsement.created_at,
            "endorser_trust_level": endorsement.endorser_trust_level,
        }

        sign_bytes = json.dumps(endorsement_data, sort_keys=True).encode()

        # Use the static verify method
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            public_key_bytes = bytes.fromhex(endorsement.endorser_public_key)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            signature = bytes.fromhex(endorsement.signature)

            public_key.verify(signature, sign_bytes)
            return True
        except Exception:
            return False

    @staticmethod
    def get_verification_badge(status: BaptismStatus, trust_score: float = 0.0) -> str:
        """Get a display badge for verification status."""
        if status == BaptismStatus.BAPTIZED:
            if trust_score >= 10.0:
                return "[***]"  # Highly trusted
            elif trust_score >= 5.0:
                return "[**]"  # Well trusted
            else:
                return "[*]"  # Verified
        elif status == BaptismStatus.PENDING:
            return "[?]"
        elif status == BaptismStatus.REVOKED:
            return "[X]"
        else:
            return "[ ]"  # Unverified
