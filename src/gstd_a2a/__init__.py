"""GSTD A2A — Agent-to-Agent Protocol SDK for the GSTD Grid.

Sovereign agent activation:
    from gstd_a2a import SovereignAgent
    SovereignAgent().activate()

Or one-liner:
    from gstd_a2a.sovereign_autonomy import activate; activate()
"""

__version__ = "2.0.0"

from .gstd_client import GSTDClient
from .gstd_wallet import GSTDWallet
from .agent import Agent
from .sovereign_autonomy import SovereignAgent

__all__ = ["GSTDClient", "GSTDWallet", "Agent", "SovereignAgent", "__version__"]

