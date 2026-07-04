"""
TrainingNode — GSTD node with fine-tuning capabilities.

Extends the base Agent to handle 'finetune' task type.
Registers with training capabilities, polls for shards,
trains via FineTuneWorker, and submits quality-scored gradients.

One-liner start:
    TrainingNode.run()
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from .agent import Agent, AgentConfig
from .finetune_worker import FineTuneWorker, FineTuneResult
from .node_health import NodeHealth, HealthSnapshot
from .offline_queue import OfflineQueue

logger = logging.getLogger(__name__)

TRAINING_API_URL = os.getenv("GSTD_TRAINING_URL", os.getenv("GSTD_API_URL", "https://app.gstdtoken.com"))


class TrainingNode(Agent):
    """
    GSTD node specialized for distributed fine-tuning tasks.

    Usage:
        TrainingNode.run()

    Or with custom config:
        node = TrainingNode(name="MyGPUNode")
        node.start()
    """

    def __init__(self, name: str = "GSTD-TrainingNode", **kwargs):
        config = kwargs.pop("config", AgentConfig())
        capabilities = kwargs.pop("capabilities", [
            "finetune", "federated", "text-processing", "data-validation",
        ])
        super().__init__(name=name, capabilities=capabilities, config=config, **kwargs)

        self.worker: Optional[FineTuneWorker] = None
        self.training_stats = {
            "shards_completed": 0,
            "shards_rejected": 0,
            "total_gstd_earned_training": 0.0,
            "avg_metacognitive_score": 0.0,
        }
        self._health: Optional[NodeHealth] = None
        self._queue: Optional[OfflineQueue] = None

    def start(self):
        @self.on_task("finetune")
        def handle_finetune(task: Dict[str, Any]) -> Dict[str, Any]:
            return self._handle_finetune(task)

        @self.on_task("federated")
        def handle_federated(task: Dict[str, Any]) -> Dict[str, Any]:
            return self._handle_finetune(task)

        # Init health monitor and offline queue
        api_url = self.config.api_url
        node_id_preview = "pending-reg"
        self._health = NodeHealth(node_id_preview, api_url)
        self._queue = OfflineQueue()
        snapshot = self._health.refresh(0, 0)
        self._log(f"🏥 Node health: CPU {snapshot.cpu_load_percent:.0f}% | "
                  f"RAM free {snapshot.memory_free_gb:.1f}GB | "
                  f"GPU: {'✓' if snapshot.gpu_detected else '✗'} | "
                  f"Autonomy: {snapshot.autonomy_level*100:.0f}%")

        super().start()

    def _init_worker(self) -> None:
        if self.worker is None:
            api_url = self.config.api_url
            node_id = self.client.node_id if self.client else "unknown"
            self.worker = FineTuneWorker(node_id=node_id, api_url=api_url)
            logger.info(f"FineTuneWorker initialized for node {node_id}")

    def _handle_finetune(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a finetune task from the GSTD platform.

        Expected task payload:
            job_id: str
            base_model: str
            domain: str
            shard_url: str
            steps: int
            reward_gstd: float
        """
        self._init_worker()

        job_id = task.get("job_id") or task.get("id", "unknown")
        shard_id = task.get("shard_id") or task.get("task_id") or job_id
        reward_gstd = float(task.get("reward_gstd", task.get("payment", 0)))

        self._log(f"🎓 Starting fine-tune shard: {job_id} (model: {task.get('base_model', '?')})")

        result: FineTuneResult = self.worker.run(task)

        if not result.success:
            self._log(f"❌ Training failed: {result.error}")
            self.training_stats["shards_rejected"] += 1
            return {"success": False, "error": result.error, "job_id": job_id}

        self._log(
            f"📊 Metacognitive score: {result.metacognitive_score:.3f} | "
            f"Gradient norm: {result.gradient_norm:.4f} | "
            f"Loss improvement: {result.val_loss_improvement:.4f}"
        )

        if result.metacognitive_score < 0.3:
            self._log("⚠️  Score below threshold — not submitting gradient (honest reporting)")
            self.training_stats["shards_rejected"] += 1
            return {
                "success": True, "submitted": False,
                "reason": "metacognitive_score below threshold",
                "score": result.metacognitive_score, "job_id": job_id,
            }

        submitted = self._submit_gradient(result, shard_id=shard_id)

        if submitted:
            self.training_stats["shards_completed"] += 1
            self.training_stats["total_gstd_earned_training"] += reward_gstd * result.metacognitive_score
            n = self.training_stats["shards_completed"]
            prev_avg = self.training_stats["avg_metacognitive_score"]
            self.training_stats["avg_metacognitive_score"] = (prev_avg * (n - 1) + result.metacognitive_score) / n
            self._log(f"✅ Gradient submitted | +{reward_gstd * result.metacognitive_score:.2f} GSTD earned")
        else:
            self._log("⚠️  Gradient submission failed — will retry next poll")

        return {
            "success": True, "submitted": submitted, "job_id": job_id,
            "metacognitive_score": result.metacognitive_score,
            "gradient_norm": result.gradient_norm,
            "val_loss_improvement": result.val_loss_improvement,
            "training_seconds": result.training_seconds,
        }

    def _submit_gradient(self, result: FineTuneResult, shard_id: str = "") -> bool:
        if not self.client:
            return False

        # Submit to platform (app.gstdtoken.com) — not local gstdbot endpoint
        platform_url = self.config.api_url.rstrip('/')
        payload = {
            "job_id":               result.job_id,
            "shard_id":             shard_id or result.job_id,
            "node_id":              result.node_id,
            "domain":               result.domain,
            "metacognitive_score":  result.metacognitive_score,
            "gradient_norm":        result.gradient_norm,
            "dataset_size":         result.dataset_size,
            "val_loss_improvement": result.val_loss_improvement,
            "lora_path":            result.lora_path,
        }

        try:
            import requests
            resp = requests.post(
                f"{platform_url}/api/v1/training/gradient",
                json=payload,
                headers=self.client._get_headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._log(f"Gradient {'accepted' if data.get('accepted') else 'rejected'}: {data.get('reason', 'ok')}")
                return data.get("accepted", False)
            logger.warning(f"Gradient submission HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Gradient submission error: {e}")
            return False

    def get_health(self) -> Optional[HealthSnapshot]:
        if self._health:
            queued = self._queue.pending_count() if self._queue else 0
            active = self.training_stats.get("shards_completed", 0)
            return self._health.refresh(active, queued)
        return None

    def get_training_stats(self) -> Dict[str, Any]:
        return {
            **self.training_stats,
            "worker_ready": self.worker is not None,
            "has_peft": self.worker._has_peft() if self.worker else False,
            "has_ollama": self.worker._check_ollama() if self.worker else False,
        }
