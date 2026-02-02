"""
Project Inkling - Test Fixtures

Shared pytest fixtures for the test suite.
"""

import os
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def identity(temp_data_dir):
    """Create a test Identity instance."""
    from core.crypto import Identity
    ident = Identity(data_dir=temp_data_dir)
    ident.initialize()
    return ident


@pytest.fixture
def second_identity(temp_data_dir):
    """Create a second Identity for testing verification."""
    from core.crypto import Identity
    # Use a subdirectory to avoid key collision
    second_dir = os.path.join(temp_data_dir, "device2")
    os.makedirs(second_dir, exist_ok=True)
    ident = Identity(data_dir=second_dir)
    ident.initialize()
    return ident


@pytest.fixture
def personality():
    """Create a test Personality instance."""
    from core.personality import Personality, PersonalityTraits
    traits = PersonalityTraits(
        curiosity=0.7,
        cheerfulness=0.6,
        verbosity=0.5,
        playfulness=0.6,
        empathy=0.7,
        independence=0.4,
    )
    return Personality(name="TestInkling", traits=traits)


@pytest.fixture
def telegram_crypto(temp_data_dir):
    """Create a TelegramCrypto instance for testing."""
    from core.telegram import TelegramCrypto
    crypto = TelegramCrypto(data_dir=temp_data_dir)
    crypto.initialize()
    return crypto


@pytest.fixture
def second_telegram_crypto(temp_data_dir):
    """Create a second TelegramCrypto for testing encryption between two parties."""
    from core.telegram import TelegramCrypto
    second_dir = os.path.join(temp_data_dir, "device2")
    os.makedirs(second_dir, exist_ok=True)
    crypto = TelegramCrypto(data_dir=second_dir)
    crypto.initialize()
    return crypto


@pytest.fixture
def rate_limiter(temp_data_dir):
    """Create a RateLimiter instance for testing."""
    from core.rate_limiter import RateLimiter
    return RateLimiter(data_dir=temp_data_dir)


@pytest.fixture
def postcard_canvas():
    """Create a PostcardCanvas instance for testing."""
    from core.postcard import PostcardCanvas
    return PostcardCanvas(width=100, height=50)
