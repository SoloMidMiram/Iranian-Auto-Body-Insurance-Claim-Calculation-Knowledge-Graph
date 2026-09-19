import pytest

from iran_auto_claim.knowledge import Knowledge


@pytest.fixture(scope="session")
def kb() -> Knowledge:
    return Knowledge.load()
