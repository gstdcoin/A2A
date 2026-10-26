"""GSTD signed platform clients and experimental integration modules.

Use GSTDClient with a persistent Ed25519 node identity. Paid work must be
funded and accepted. Training/autonomy modules are research APIs, not a
promise of deployed service, automatic rewards or production isolation.
"""

__version__ = "2.1.2"

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
