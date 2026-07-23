"""GSTD A2A — Agent-to-Agent Protocol SDK for the GSTD Grid.

Sovereign agent activation:
    from gstd_a2a import SovereignAgent
    SovereignAgent().activate()

Training node (earn GSTD by fine-tuning models):
    from gstd_a2a import TrainingNode
    TrainingNode.run()

Or one-liner:
    from gstd_a2a.sovereign_autonomy import activate; activate()
"""

__version__ = "2.1.0"

from .gstd_client import GSTDClient
from .gstd_wallet import GSTDWallet
from .agent import Agent
from .sovereign_autonomy import SovereignAgent
from .training_node import TrainingNode
from .finetune_worker import FineTuneWorker
from .metacognition import MetacognitiveEvaluator
from .node_health import NodeHealth
from .offline_queue import OfflineQueue
from .llm_service import LLMService

__all__ = [
    "GSTDClient", "GSTDWallet", "Agent", "SovereignAgent",
    "TrainingNode", "FineTuneWorker", "MetacognitiveEvaluator",
    "NodeHealth", "OfflineQueue", "LLMService",
    "__version__",
]
