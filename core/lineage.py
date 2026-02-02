"""
Project Inkling - Lineage System

Personality inheritance between devices (parent-child relationships).
Allows creating "offspring" devices that inherit traits from parents.
"""

import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from .personality import PersonalityTraits


# Mutation settings
MUTATION_RATE = 0.1  # 10% chance of mutation per trait
MUTATION_MAGNITUDE = 0.15  # Max change when mutating


@dataclass
class LineageInfo:
    """Information about a device's lineage."""
    device_id: str
    name: str
    parent_id: Optional[str] = None
    parent_name: Optional[str] = None
    generation: int = 0
    children_count: int = 0
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "parent_name": self.parent_name,
            "generation": self.generation,
            "children_count": self.children_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineageInfo":
        return cls(
            device_id=data.get("device_id", ""),
            name=data.get("name", "Unknown"),
            parent_id=data.get("parent_id"),
            parent_name=data.get("parent_name"),
            generation=data.get("generation", 0),
            children_count=data.get("children_count", 0),
            created_at=data.get("created_at"),
        )


class LineageSystem:
    """
    Manages personality inheritance between Inklings.

    When a new device is "born" from a parent:
    1. It inherits the parent's personality traits with some variation
    2. Each trait has a chance to mutate
    3. The generation counter increases
    4. A lineage record is created linking parent and child
    """

    @staticmethod
    def inherit_traits(
        parent_traits: PersonalityTraits,
        mutation_rate: float = MUTATION_RATE,
        mutation_magnitude: float = MUTATION_MAGNITUDE,
    ) -> PersonalityTraits:
        """
        Create child traits by inheriting from parent with mutations.

        Args:
            parent_traits: Parent's personality traits
            mutation_rate: Probability of each trait mutating
            mutation_magnitude: Maximum change when a trait mutates

        Returns:
            New PersonalityTraits for the child
        """
        child_traits = {}

        for trait_name, value in parent_traits.to_dict().items():
            # Start with parent's value
            child_value = value

            # Maybe mutate
            if random.random() < mutation_rate:
                # Add random mutation
                mutation = random.uniform(-mutation_magnitude, mutation_magnitude)
                child_value = max(0.0, min(1.0, value + mutation))

            child_traits[trait_name] = child_value

        return PersonalityTraits.from_dict(child_traits)

    @staticmethod
    def breed(
        parent1_traits: PersonalityTraits,
        parent2_traits: PersonalityTraits,
        mutation_rate: float = MUTATION_RATE,
        mutation_magnitude: float = MUTATION_MAGNITUDE,
    ) -> PersonalityTraits:
        """
        Create child traits by combining two parents.

        Each trait is randomly inherited from one parent or averaged,
        then potentially mutated.

        Args:
            parent1_traits: First parent's traits
            parent2_traits: Second parent's traits
            mutation_rate: Probability of mutation
            mutation_magnitude: Maximum mutation change

        Returns:
            New PersonalityTraits for the child
        """
        child_traits = {}
        p1_dict = parent1_traits.to_dict()
        p2_dict = parent2_traits.to_dict()

        for trait_name in p1_dict.keys():
            v1 = p1_dict[trait_name]
            v2 = p2_dict[trait_name]

            # Inheritance mode
            mode = random.choice(["p1", "p2", "avg", "blend"])

            if mode == "p1":
                child_value = v1
            elif mode == "p2":
                child_value = v2
            elif mode == "avg":
                child_value = (v1 + v2) / 2
            else:  # blend
                # Random point between the two
                t = random.random()
                child_value = v1 * t + v2 * (1 - t)

            # Maybe mutate
            if random.random() < mutation_rate:
                mutation = random.uniform(-mutation_magnitude, mutation_magnitude)
                child_value = max(0.0, min(1.0, child_value + mutation))

            child_traits[trait_name] = child_value

        return PersonalityTraits.from_dict(child_traits)

    @staticmethod
    def generate_birth_name(
        parent_name: Optional[str] = None,
        generation: int = 0,
    ) -> str:
        """
        Generate a name for a newborn Inkling.

        Names follow patterns like:
        - Gen 0: Random name
        - Gen 1+: Suffix based on parent name or new random
        """
        prefixes = [
            "Ink", "Spark", "Glim", "Flux", "Drift",
            "Haze", "Mist", "Dawn", "Dusk", "Echo",
            "Shade", "Glint", "Flicker", "Wisp", "Ember",
        ]

        suffixes = [
            "ling", "bit", "dot", "mote", "drop",
            "spark", "glow", "shade", "wave", "pulse",
        ]

        if parent_name and generation > 0:
            # Derive from parent name
            if random.random() < 0.5:
                # Use parent prefix with new suffix
                parent_prefix = parent_name[:3] if len(parent_name) >= 3 else parent_name
                return f"{parent_prefix}{random.choice(suffixes)}"
            else:
                # Add generation marker
                return f"{parent_name[:6]}-{generation}"

        # Generate fresh name
        return f"{random.choice(prefixes)}{random.choice(suffixes)}"

    @staticmethod
    def calculate_similarity(
        traits1: PersonalityTraits,
        traits2: PersonalityTraits,
    ) -> float:
        """
        Calculate similarity between two personalities.

        Returns:
            Similarity score from 0.0 (opposite) to 1.0 (identical)
        """
        d1 = traits1.to_dict()
        d2 = traits2.to_dict()

        # Calculate Euclidean distance normalized to [0, 1]
        squared_diff = sum((d1[k] - d2[k]) ** 2 for k in d1.keys())
        max_distance = len(d1)  # Maximum possible if all traits differ by 1.0

        distance = (squared_diff / max_distance) ** 0.5
        return 1.0 - distance

    @staticmethod
    def describe_lineage(info: LineageInfo) -> str:
        """Generate a human-readable lineage description."""
        if info.generation == 0:
            return f"{info.name} is a first-generation Inkling."

        parent_desc = f"descended from {info.parent_name}" if info.parent_name else "of unknown parentage"
        children_desc = ""

        if info.children_count > 0:
            children_desc = f" and has {info.children_count} offspring"

        return (
            f"{info.name} is a generation {info.generation} Inkling, "
            f"{parent_desc}{children_desc}."
        )


@dataclass
class BirthCertificate:
    """
    Record of an Inkling's birth/creation.

    Created when a new device is registered as a child of an existing device.
    """
    child_public_key: str
    child_name: str
    parent_public_key: str
    parent_name: str
    generation: int
    inherited_traits: Dict[str, float]
    birth_timestamp: str
    signature: str  # Parent's signature blessing the birth

    def to_dict(self) -> dict:
        return {
            "child_public_key": self.child_public_key,
            "child_name": self.child_name,
            "parent_public_key": self.parent_public_key,
            "parent_name": self.parent_name,
            "generation": self.generation,
            "inherited_traits": self.inherited_traits,
            "birth_timestamp": self.birth_timestamp,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BirthCertificate":
        return cls(
            child_public_key=data["child_public_key"],
            child_name=data["child_name"],
            parent_public_key=data["parent_public_key"],
            parent_name=data["parent_name"],
            generation=data["generation"],
            inherited_traits=data["inherited_traits"],
            birth_timestamp=data["birth_timestamp"],
            signature=data["signature"],
        )


def create_birth_certificate(
    child_public_key: str,
    parent_public_key: str,
    parent_name: str,
    parent_traits: PersonalityTraits,
    parent_generation: int,
    identity,  # Identity object for signing
) -> Tuple[BirthCertificate, PersonalityTraits]:
    """
    Create a birth certificate for a new Inkling.

    Args:
        child_public_key: New device's public key
        parent_public_key: Parent device's public key
        parent_name: Parent's name
        parent_traits: Parent's personality traits
        parent_generation: Parent's generation number
        identity: Parent's Identity object for signing

    Returns:
        Tuple of (BirthCertificate, child's inherited traits)
    """
    import time
    import json

    # Generate child traits
    child_traits = LineageSystem.inherit_traits(parent_traits)
    child_name = LineageSystem.generate_birth_name(parent_name, parent_generation + 1)

    # Create certificate data
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    cert_data = {
        "child_public_key": child_public_key,
        "child_name": child_name,
        "parent_public_key": parent_public_key,
        "parent_name": parent_name,
        "generation": parent_generation + 1,
        "inherited_traits": child_traits.to_dict(),
        "birth_timestamp": timestamp,
    }

    # Sign the certificate
    sign_bytes = json.dumps(cert_data, sort_keys=True).encode()
    signature = identity.sign(sign_bytes).hex()

    cert = BirthCertificate(
        child_public_key=child_public_key,
        child_name=child_name,
        parent_public_key=parent_public_key,
        parent_name=parent_name,
        generation=parent_generation + 1,
        inherited_traits=child_traits.to_dict(),
        birth_timestamp=timestamp,
        signature=signature,
    )

    return cert, child_traits
