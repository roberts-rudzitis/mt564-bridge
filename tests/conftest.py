import pytest

from helpers import ROOT
from mt564_bridge.config import load_config


@pytest.fixture(scope="session")
def config():
    """The repository's own bridge.toml, with every path resolved."""
    return load_config(ROOT / "bridge.toml")
