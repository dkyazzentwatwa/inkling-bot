"""
Project Inkling - Lineage Tests

Tests for core/lineage.py - personality inheritance and birth certificates.
"""

import pytest
import random


class TestLineageInfo:
    """Tests for LineageInfo dataclass."""

    def test_lineage_info_defaults(self):
        """Test LineageInfo default values."""
        from core.lineage import LineageInfo

        info = LineageInfo(device_id="dev123", name="TestInkling")

        assert info.device_id == "dev123"
        assert info.name == "TestInkling"
        assert info.parent_id is None
        assert info.generation == 0
        assert info.children_count == 0

    def test_lineage_info_to_dict(self):
        """Test LineageInfo serialization."""
        from core.lineage import LineageInfo

        info = LineageInfo(
            device_id="dev123",
            name="TestInkling",
            parent_id="parent456",
            parent_name="ParentInkling",
            generation=2,
            children_count=3,
        )

        d = info.to_dict()

        assert d["device_id"] == "dev123"
        assert d["name"] == "TestInkling"
        assert d["parent_id"] == "parent456"
        assert d["parent_name"] == "ParentInkling"
        assert d["generation"] == 2
        assert d["children_count"] == 3

    def test_lineage_info_from_dict(self):
        """Test LineageInfo deserialization."""
        from core.lineage import LineageInfo

        data = {
            "device_id": "dev789",
            "name": "RestoredInkling",
            "parent_id": "parent123",
            "generation": 1,
        }

        info = LineageInfo.from_dict(data)

        assert info.device_id == "dev789"
        assert info.name == "RestoredInkling"
        assert info.parent_id == "parent123"
        assert info.generation == 1


class TestLineageSystem:
    """Tests for LineageSystem inheritance logic."""

    def test_inherit_traits_preserves_structure(self):
        """Test that inherited traits have all expected fields."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        parent = PersonalityTraits(
            curiosity=0.7,
            cheerfulness=0.6,
            verbosity=0.5,
            playfulness=0.6,
            empathy=0.7,
            independence=0.4,
        )

        child = LineageSystem.inherit_traits(parent)

        assert hasattr(child, "curiosity")
        assert hasattr(child, "cheerfulness")
        assert hasattr(child, "verbosity")
        assert hasattr(child, "playfulness")
        assert hasattr(child, "empathy")
        assert hasattr(child, "independence")

    def test_inherit_traits_with_no_mutation(self):
        """Test inheritance with 0% mutation rate."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        parent = PersonalityTraits(curiosity=0.8, cheerfulness=0.3)

        child = LineageSystem.inherit_traits(parent, mutation_rate=0.0)

        # Should be identical
        assert child.curiosity == parent.curiosity
        assert child.cheerfulness == parent.cheerfulness

    def test_inherit_traits_with_full_mutation(self):
        """Test inheritance with 100% mutation rate."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        random.seed(42)  # For reproducibility

        parent = PersonalityTraits(curiosity=0.5, cheerfulness=0.5)

        child = LineageSystem.inherit_traits(
            parent, mutation_rate=1.0, mutation_magnitude=0.2
        )

        # At least one trait should be different
        # (with 100% mutation rate, all should change)
        parent_dict = parent.to_dict()
        child_dict = child.to_dict()

        differences = sum(
            1 for k in parent_dict if parent_dict[k] != child_dict[k]
        )
        assert differences > 0

    def test_inherit_traits_bounded(self):
        """Test that inherited traits are bounded to [0, 1]."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        # Extreme values
        parent = PersonalityTraits(curiosity=0.0, cheerfulness=1.0)

        # Run many times with high mutation to test bounds
        for _ in range(20):
            child = LineageSystem.inherit_traits(
                parent, mutation_rate=1.0, mutation_magnitude=0.5
            )
            child_dict = child.to_dict()

            for value in child_dict.values():
                assert 0.0 <= value <= 1.0

    def test_breed_two_parents(self):
        """Test breeding from two parents."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        random.seed(42)

        parent1 = PersonalityTraits(curiosity=0.9, cheerfulness=0.1)
        parent2 = PersonalityTraits(curiosity=0.1, cheerfulness=0.9)

        child = LineageSystem.breed(parent1, parent2, mutation_rate=0.0)

        # With no mutation, traits should come from parents
        # (either p1, p2, average, or blend)
        assert 0.1 <= child.curiosity <= 0.9
        assert 0.1 <= child.cheerfulness <= 0.9

    def test_breed_with_mutation(self):
        """Test breeding with mutations."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        parent1 = PersonalityTraits(curiosity=0.5, cheerfulness=0.5)
        parent2 = PersonalityTraits(curiosity=0.5, cheerfulness=0.5)

        # With identical parents and mutation, child should differ
        child = LineageSystem.breed(
            parent1, parent2, mutation_rate=1.0, mutation_magnitude=0.3
        )

        # At least some traits should differ from 0.5
        child_dict = child.to_dict()
        differences = sum(1 for v in child_dict.values() if v != 0.5)
        assert differences > 0


class TestNameGeneration:
    """Tests for name generation."""

    def test_generate_fresh_name(self):
        """Test generating a name for gen 0."""
        from core.lineage import LineageSystem

        random.seed(42)

        name = LineageSystem.generate_birth_name(parent_name=None, generation=0)

        assert isinstance(name, str)
        assert len(name) > 0

    def test_generate_derived_name(self):
        """Test generating a name derived from parent."""
        from core.lineage import LineageSystem

        random.seed(42)

        name = LineageSystem.generate_birth_name(
            parent_name="Sparkle", generation=1
        )

        assert isinstance(name, str)
        assert len(name) > 0

    def test_name_generation_deterministic(self):
        """Test that name generation is deterministic with seed."""
        from core.lineage import LineageSystem

        random.seed(123)
        name1 = LineageSystem.generate_birth_name(generation=0)

        random.seed(123)
        name2 = LineageSystem.generate_birth_name(generation=0)

        assert name1 == name2


class TestSimilarityCalculation:
    """Tests for personality similarity calculation."""

    def test_identical_traits_similarity(self):
        """Test that identical traits have similarity of 1.0."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        traits1 = PersonalityTraits(curiosity=0.5, cheerfulness=0.5)
        traits2 = PersonalityTraits(curiosity=0.5, cheerfulness=0.5)

        similarity = LineageSystem.calculate_similarity(traits1, traits2)

        assert similarity == 1.0

    def test_opposite_traits_similarity(self):
        """Test that opposite traits have low similarity."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        traits1 = PersonalityTraits(
            curiosity=0.0, cheerfulness=0.0, verbosity=0.0,
            playfulness=0.0, empathy=0.0, independence=0.0
        )
        traits2 = PersonalityTraits(
            curiosity=1.0, cheerfulness=1.0, verbosity=1.0,
            playfulness=1.0, empathy=1.0, independence=1.0
        )

        similarity = LineageSystem.calculate_similarity(traits1, traits2)

        assert similarity == 0.0

    def test_partial_similarity(self):
        """Test partially similar traits."""
        from core.lineage import LineageSystem
        from core.personality import PersonalityTraits

        traits1 = PersonalityTraits(curiosity=0.5, cheerfulness=0.5)
        traits2 = PersonalityTraits(curiosity=0.7, cheerfulness=0.3)

        similarity = LineageSystem.calculate_similarity(traits1, traits2)

        assert 0.0 < similarity < 1.0


class TestLineageDescription:
    """Tests for lineage description generation."""

    def test_describe_first_gen(self):
        """Test describing a first-generation Inkling."""
        from core.lineage import LineageSystem, LineageInfo

        info = LineageInfo(
            device_id="dev123",
            name="Sparkle",
            generation=0,
        )

        desc = LineageSystem.describe_lineage(info)

        assert "Sparkle" in desc
        assert "first-generation" in desc

    def test_describe_with_parent(self):
        """Test describing an Inkling with parent."""
        from core.lineage import LineageSystem, LineageInfo

        info = LineageInfo(
            device_id="dev123",
            name="Sparkle Jr",
            parent_id="parent456",
            parent_name="Sparkle",
            generation=2,
        )

        desc = LineageSystem.describe_lineage(info)

        assert "Sparkle Jr" in desc
        assert "generation 2" in desc
        assert "descended from Sparkle" in desc

    def test_describe_with_children(self):
        """Test describing an Inkling with offspring."""
        from core.lineage import LineageSystem, LineageInfo

        info = LineageInfo(
            device_id="dev123",
            name="Matriarch",
            generation=1,
            parent_name="Genesis",
            children_count=5,
        )

        desc = LineageSystem.describe_lineage(info)

        assert "5 offspring" in desc


class TestBirthCertificate:
    """Tests for BirthCertificate dataclass."""

    def test_birth_certificate_to_dict(self):
        """Test BirthCertificate serialization."""
        from core.lineage import BirthCertificate

        cert = BirthCertificate(
            child_public_key="child_key_123",
            child_name="Baby",
            parent_public_key="parent_key_456",
            parent_name="Parent",
            generation=1,
            inherited_traits={"curiosity": 0.7},
            birth_timestamp="2024-01-01T00:00:00Z",
            signature="sig_abc",
        )

        d = cert.to_dict()

        assert d["child_public_key"] == "child_key_123"
        assert d["child_name"] == "Baby"
        assert d["parent_public_key"] == "parent_key_456"
        assert d["generation"] == 1
        assert d["inherited_traits"]["curiosity"] == 0.7

    def test_birth_certificate_from_dict(self):
        """Test BirthCertificate deserialization."""
        from core.lineage import BirthCertificate

        data = {
            "child_public_key": "child_key",
            "child_name": "Child",
            "parent_public_key": "parent_key",
            "parent_name": "Parent",
            "generation": 2,
            "inherited_traits": {"empathy": 0.8},
            "birth_timestamp": "2024-01-01T00:00:00Z",
            "signature": "signature",
        }

        cert = BirthCertificate.from_dict(data)

        assert cert.child_name == "Child"
        assert cert.generation == 2


class TestCreateBirthCertificate:
    """Tests for birth certificate creation."""

    def test_create_birth_certificate(self, identity):
        """Test creating a signed birth certificate."""
        from core.lineage import create_birth_certificate
        from core.personality import PersonalityTraits

        parent_traits = PersonalityTraits(curiosity=0.8, cheerfulness=0.7)

        cert, child_traits = create_birth_certificate(
            child_public_key="new_device_key",
            parent_public_key=identity.public_key_hex,
            parent_name="ParentInkling",
            parent_traits=parent_traits,
            parent_generation=0,
            identity=identity,
        )

        assert cert.child_public_key == "new_device_key"
        assert cert.parent_public_key == identity.public_key_hex
        assert cert.parent_name == "ParentInkling"
        assert cert.generation == 1
        assert len(cert.signature) > 0
        assert child_traits is not None
