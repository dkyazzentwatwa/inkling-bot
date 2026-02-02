"""
Project Inkling - Baptism Tests

Tests for core/baptism.py - web of trust and device verification.
"""

import pytest


class TestBaptismStatus:
    """Tests for BaptismStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        from core.baptism import BaptismStatus

        assert BaptismStatus.UNBAPTIZED.value == "unbaptized"
        assert BaptismStatus.PENDING.value == "pending"
        assert BaptismStatus.BAPTIZED.value == "baptized"
        assert BaptismStatus.REVOKED.value == "revoked"


class TestBaptismRequest:
    """Tests for BaptismRequest dataclass."""

    def test_baptism_request_to_dict(self):
        """Test BaptismRequest serialization."""
        from core.baptism import BaptismRequest

        request = BaptismRequest(
            requester_public_key="pub_key_123",
            requester_name="NewInkling",
            requester_hardware_hash="hw_hash_456",
            message="Please verify me!",
            created_at="2024-01-01T00:00:00Z",
            signature="sig_789",
        )

        d = request.to_dict()

        assert d["requester_public_key"] == "pub_key_123"
        assert d["requester_name"] == "NewInkling"
        assert d["requester_hardware_hash"] == "hw_hash_456"
        assert d["message"] == "Please verify me!"
        assert d["signature"] == "sig_789"

    def test_baptism_request_from_dict(self):
        """Test BaptismRequest deserialization."""
        from core.baptism import BaptismRequest

        data = {
            "requester_public_key": "key",
            "requester_name": "Test",
            "requester_hardware_hash": "hash",
            "message": "",
            "created_at": "2024-01-01T00:00:00Z",
            "signature": "sig",
        }

        request = BaptismRequest.from_dict(data)

        assert request.requester_name == "Test"


class TestBaptismEndorsement:
    """Tests for BaptismEndorsement dataclass."""

    def test_endorsement_to_dict(self):
        """Test BaptismEndorsement serialization."""
        from core.baptism import BaptismEndorsement

        endorsement = BaptismEndorsement(
            endorser_public_key="endorser_key",
            endorser_name="TrustedInkling",
            endorsed_public_key="endorsed_key",
            endorsed_name="NewInkling",
            message="I vouch for this device",
            created_at="2024-01-01T00:00:00Z",
            signature="endorsement_sig",
            endorser_trust_level=2,
        )

        d = endorsement.to_dict()

        assert d["endorser_public_key"] == "endorser_key"
        assert d["endorsed_name"] == "NewInkling"
        assert d["endorser_trust_level"] == 2

    def test_endorsement_from_dict(self):
        """Test BaptismEndorsement deserialization."""
        from core.baptism import BaptismEndorsement

        data = {
            "endorser_public_key": "key1",
            "endorser_name": "Endorser",
            "endorsed_public_key": "key2",
            "endorsed_name": "Endorsed",
            "message": "Good",
            "created_at": "2024-01-01T00:00:00Z",
            "signature": "sig",
            "endorser_trust_level": 3,
        }

        endorsement = BaptismEndorsement.from_dict(data)

        assert endorsement.endorser_trust_level == 3

    def test_endorsement_default_trust_level(self):
        """Test that default trust level is 1."""
        from core.baptism import BaptismEndorsement

        data = {
            "endorser_public_key": "key1",
            "endorser_name": "Endorser",
            "endorsed_public_key": "key2",
            "endorsed_name": "Endorsed",
            "message": "",
            "created_at": "2024-01-01T00:00:00Z",
            "signature": "sig",
        }

        endorsement = BaptismEndorsement.from_dict(data)

        assert endorsement.endorser_trust_level == 1


class TestTrustChain:
    """Tests for TrustChain dataclass."""

    def test_trust_chain_to_dict(self):
        """Test TrustChain serialization."""
        from core.baptism import TrustChain, BaptismStatus

        chain = TrustChain(
            device_public_key="dev_key",
            device_name="TestDevice",
            status=BaptismStatus.BAPTIZED,
            trust_score=5.0,
        )

        d = chain.to_dict()

        assert d["device_public_key"] == "dev_key"
        assert d["device_name"] == "TestDevice"
        assert d["status"] == "baptized"
        assert d["trust_score"] == 5.0

    def test_trust_chain_from_dict(self):
        """Test TrustChain deserialization."""
        from core.baptism import TrustChain, BaptismStatus

        data = {
            "device_public_key": "key",
            "device_name": "Device",
            "endorsements": [],
            "status": "pending",
            "trust_score": 1.5,
        }

        chain = TrustChain.from_dict(data)

        assert chain.status == BaptismStatus.PENDING
        assert chain.trust_score == 1.5


class TestBaptismSystem:
    """Tests for BaptismSystem logic."""

    def test_calculate_trust_score_empty(self):
        """Test trust score with no endorsements."""
        from core.baptism import BaptismSystem

        score = BaptismSystem.calculate_trust_score([])

        assert score == 0.0

    def test_calculate_trust_score_single(self):
        """Test trust score with single endorsement."""
        from core.baptism import BaptismSystem, BaptismEndorsement

        endorsement = BaptismEndorsement(
            endorser_public_key="key",
            endorser_name="Endorser",
            endorsed_public_key="key2",
            endorsed_name="Endorsed",
            message="",
            created_at="2024-01-01T00:00:00Z",
            signature="sig",
            endorser_trust_level=2,
        )

        score = BaptismSystem.calculate_trust_score([endorsement])

        assert score == 2.0

    def test_calculate_trust_score_multiple(self):
        """Test trust score with multiple endorsements."""
        from core.baptism import BaptismSystem, BaptismEndorsement

        def make_endorsement(trust_level):
            return BaptismEndorsement(
                endorser_public_key=f"key{trust_level}",
                endorser_name=f"Endorser{trust_level}",
                endorsed_public_key="target",
                endorsed_name="Target",
                message="",
                created_at="2024-01-01T00:00:00Z",
                signature="sig",
                endorser_trust_level=trust_level,
            )

        endorsements = [make_endorsement(2), make_endorsement(1), make_endorsement(1)]

        score = BaptismSystem.calculate_trust_score(endorsements)

        # First (highest) counts full, others have diminishing returns
        # 2 * 1.0 + 1 * (1/1.3) + 1 * (1/1.6) ≈ 2 + 0.77 + 0.625
        assert score > 3.0
        assert score < 4.0

    def test_check_eligibility_not_enough_endorsements(self):
        """Test eligibility with insufficient endorsements."""
        from core.baptism import BaptismSystem, BaptismEndorsement

        endorsement = BaptismEndorsement(
            endorser_public_key="key",
            endorser_name="Endorser",
            endorsed_public_key="key2",
            endorsed_name="Endorsed",
            message="",
            created_at="2024-01-01T00:00:00Z",
            signature="sig",
            endorser_trust_level=5,
        )

        eligible, score, reason = BaptismSystem.check_baptism_eligibility(
            [endorsement], min_endorsements=2
        )

        assert eligible is False
        assert "more endorsement" in reason

    def test_check_eligibility_insufficient_trust(self):
        """Test eligibility with low trust score."""
        from core.baptism import BaptismSystem, BaptismEndorsement

        def make_endorsement():
            return BaptismEndorsement(
                endorser_public_key="key",
                endorser_name="Endorser",
                endorsed_public_key="key2",
                endorsed_name="Endorsed",
                message="",
                created_at="2024-01-01T00:00:00Z",
                signature="sig",
                endorser_trust_level=1,  # Low trust
            )

        endorsements = [make_endorsement(), make_endorsement()]

        eligible, score, reason = BaptismSystem.check_baptism_eligibility(
            endorsements, min_endorsements=2, trust_threshold=5.0
        )

        assert eligible is False
        assert "Trust score" in reason

    def test_check_eligibility_success(self):
        """Test successful eligibility check."""
        from core.baptism import BaptismSystem, BaptismEndorsement

        def make_endorsement(trust_level):
            return BaptismEndorsement(
                endorser_public_key=f"key{trust_level}",
                endorser_name=f"Endorser{trust_level}",
                endorsed_public_key="target",
                endorsed_name="Target",
                message="",
                created_at="2024-01-01T00:00:00Z",
                signature="sig",
                endorser_trust_level=trust_level,
            )

        # High trust endorsements
        endorsements = [make_endorsement(3), make_endorsement(2)]

        eligible, score, reason = BaptismSystem.check_baptism_eligibility(
            endorsements, min_endorsements=2, trust_threshold=3.0
        )

        assert eligible is True
        assert "Eligible" in reason

    def test_create_baptism_request(self, identity):
        """Test creating a baptism request."""
        from core.baptism import BaptismSystem

        request = BaptismSystem.create_baptism_request(
            identity=identity,
            device_name="MyInkling",
            message="Please verify me",
        )

        assert request.requester_public_key == identity.public_key_hex
        assert request.requester_name == "MyInkling"
        assert request.requester_hardware_hash == identity.hardware_hash
        assert request.message == "Please verify me"
        assert len(request.signature) > 0

    def test_create_endorsement(self, identity):
        """Test creating an endorsement."""
        from core.baptism import BaptismSystem

        endorsement = BaptismSystem.create_endorsement(
            identity=identity,
            endorser_name="TrustedDevice",
            endorsed_public_key="target_device_key",
            endorsed_name="NewDevice",
            message="I know this device",
            trust_level=2,
        )

        assert endorsement.endorser_public_key == identity.public_key_hex
        assert endorsement.endorser_name == "TrustedDevice"
        assert endorsement.endorsed_public_key == "target_device_key"
        assert endorsement.endorsed_name == "NewDevice"
        assert endorsement.endorser_trust_level == 2
        assert len(endorsement.signature) > 0

    def test_verify_endorsement_signature_valid(self, identity):
        """Test verifying a valid endorsement signature."""
        from core.baptism import BaptismSystem

        endorsement = BaptismSystem.create_endorsement(
            identity=identity,
            endorser_name="Endorser",
            endorsed_public_key="target_key",
            endorsed_name="Target",
        )

        result = BaptismSystem.verify_endorsement_signature(endorsement)

        assert result is True

    def test_verify_endorsement_signature_tampered(self, identity):
        """Test that tampered endorsement fails verification."""
        from core.baptism import BaptismSystem

        endorsement = BaptismSystem.create_endorsement(
            identity=identity,
            endorser_name="Endorser",
            endorsed_public_key="target_key",
            endorsed_name="Target",
        )

        # Tamper with the endorsement
        endorsement.message = "Tampered message"

        result = BaptismSystem.verify_endorsement_signature(endorsement)

        assert result is False


class TestVerificationBadge:
    """Tests for verification badge generation."""

    def test_badge_unbaptized(self):
        """Test badge for unbaptized device."""
        from core.baptism import BaptismSystem, BaptismStatus

        badge = BaptismSystem.get_verification_badge(BaptismStatus.UNBAPTIZED)

        assert badge == "[ ]"

    def test_badge_pending(self):
        """Test badge for pending device."""
        from core.baptism import BaptismSystem, BaptismStatus

        badge = BaptismSystem.get_verification_badge(BaptismStatus.PENDING)

        assert badge == "[?]"

    def test_badge_revoked(self):
        """Test badge for revoked device."""
        from core.baptism import BaptismSystem, BaptismStatus

        badge = BaptismSystem.get_verification_badge(BaptismStatus.REVOKED)

        assert badge == "[X]"

    def test_badge_baptized_low_trust(self):
        """Test badge for baptized device with low trust."""
        from core.baptism import BaptismSystem, BaptismStatus

        badge = BaptismSystem.get_verification_badge(
            BaptismStatus.BAPTIZED, trust_score=3.0
        )

        assert badge == "[*]"

    def test_badge_baptized_medium_trust(self):
        """Test badge for baptized device with medium trust."""
        from core.baptism import BaptismSystem, BaptismStatus

        badge = BaptismSystem.get_verification_badge(
            BaptismStatus.BAPTIZED, trust_score=7.0
        )

        assert badge == "[**]"

    def test_badge_baptized_high_trust(self):
        """Test badge for baptized device with high trust."""
        from core.baptism import BaptismSystem, BaptismStatus

        badge = BaptismSystem.get_verification_badge(
            BaptismStatus.BAPTIZED, trust_score=15.0
        )

        assert badge == "[***]"
