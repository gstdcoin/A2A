"""
NodeHealth — autonomous self-diagnostics for GSTD training nodes.

Steiniger principle: every node must know its own state and report honestly.
A node that overcommits degrades the network. A node that self-reports
accurately enables the ThermalRouter to make better decisions.
"""

import os
import time
import math
import logging
import subprocess
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class HealthSnapshot:
    node_id: str
    timestamp: float
    cpu_load_percent: float
    cpu_cores: int
    memory_total_gb: float
    memory_free_gb: float
    memory_usage_percent: float
    gpu_detected: bool
    gpu_model: str
    gpu_vram_total_gb: float
    gpu_vram_free_gb: float
    gpu_temp_celsius: float
    gpu_usage_percent: float
    platform_reachable: bool
    platform_latency_ms: float
    offline_minutes: int
    active_jobs: int
    queued_locally: int
    accepts_tasks: bool
    autonomy_level: float   # 0.0–1.0


class NodeHealth:
    """
    Monitors node resources and computes autonomy level.

    autonomy_level reflects how independently a node can operate:
    - 1.0: full GPU + local queue + platform reachable
    - 0.5: CPU only, some local work queued
    - 0.1: bare minimum (just running)
    """

    def __init__(self, node_id: str, platform_url: str):
        self.node_id = node_id
        self.platform_url = platform_url.rstrip('/')
        self._offline_since: Optional[float] = None
        self._snapshot: Optional[HealthSnapshot] = None

    def refresh(self, active_jobs: int = 0, queued_locally: int = 0) -> HealthSnapshot:
        cpu_load, cpu_cores = self._get_cpu()
        mem_total, mem_free = self._get_memory()
        gpu = self._get_gpu()
        platform_ok, latency_ms, offline_minutes = self._check_platform()

        mem_usage = (1 - mem_free / max(mem_total, 0.001)) * 100
        accepts_tasks = cpu_load < 85.0 and mem_free > 0.5 and active_jobs < 3

        autonomy = self._compute_autonomy(gpu['detected'], platform_ok, queued_locally)

        self._snapshot = HealthSnapshot(
            node_id=self.node_id,
            timestamp=time.time(),
            cpu_load_percent=cpu_load,
            cpu_cores=cpu_cores,
            memory_total_gb=round(mem_total, 2),
            memory_free_gb=round(mem_free, 2),
            memory_usage_percent=round(mem_usage, 1),
            gpu_detected=gpu['detected'],
            gpu_model=gpu.get('model', 'none'),
            gpu_vram_total_gb=gpu.get('vram_total_gb', 0.0),
            gpu_vram_free_gb=gpu.get('vram_free_gb', 0.0),
            gpu_temp_celsius=gpu.get('temp_celsius', 0.0),
            gpu_usage_percent=gpu.get('usage_percent', 0.0),
            platform_reachable=platform_ok,
            platform_latency_ms=latency_ms,
            offline_minutes=offline_minutes,
            active_jobs=active_jobs,
            queued_locally=queued_locally,
            accepts_tasks=accepts_tasks,
            autonomy_level=autonomy,
        )
        return self._snapshot

    def get(self) -> Optional[HealthSnapshot]:
        return self._snapshot

    def to_dict(self) -> Dict[str, Any]:
        if self._snapshot is None:
            return {}
        return asdict(self._snapshot)

    def _compute_autonomy(self, has_gpu: bool, platform_ok: bool, queued_locally: int) -> float:
        score = 0.1  # base: just running
        if has_gpu:
            score += 0.4  # can train locally
        if queued_locally > 0:
            score += 0.3  # has offline work
        if platform_ok:
            score += 0.2  # can coordinate
        return round(min(1.0, score), 3)

    def _get_cpu(self):
        try:
            import os as _os
            load = _os.getloadavg()[0]
            cores = _os.cpu_count() or 1
            return round(min(100.0, load / cores * 100), 1), cores
        except Exception:
            return 50.0, 1

    def _get_memory(self):
        try:
            import os as _os
            stats = _os.statvfs('/')
            # Use /proc/meminfo for actual RAM
            with open('/proc/meminfo') as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    mem[parts[0].rstrip(':')] = int(parts[1])
            total_gb = mem.get('MemTotal', 0) / 1024 / 1024
            free_gb = (mem.get('MemAvailable', mem.get('MemFree', 0))) / 1024 / 1024
            return total_gb, free_gb
        except Exception:
            return 8.0, 2.0

    def _get_gpu(self) -> Dict[str, Any]:
        try:
            out = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.free,temperature.gpu,utilization.gpu',
                 '--format=csv,noheader,nounits'],
                timeout=3, stderr=subprocess.DEVNULL
            ).decode().strip()
            parts = [p.strip() for p in out.split(',')]
            return {
                'detected': True,
                'model': parts[0] if parts else 'Unknown',
                'vram_total_gb': round(int(parts[1]) / 1024, 2) if len(parts) > 1 else 0.0,
                'vram_free_gb': round(int(parts[2]) / 1024, 2) if len(parts) > 2 else 0.0,
                'temp_celsius': float(parts[3]) if len(parts) > 3 else 0.0,
                'usage_percent': float(parts[4]) if len(parts) > 4 else 0.0,
            }
        except Exception:
            return {'detected': False, 'model': 'none'}

    def _check_platform(self):
        import urllib.request
        start = time.time()
        try:
            urllib.request.urlopen(f"{self.platform_url}/api/v1/health", timeout=3)
            latency_ms = (time.time() - start) * 1000
            self._offline_since = None
            return True, round(latency_ms, 1), 0
        except Exception:
            if self._offline_since is None:
                self._offline_since = time.time()
            offline_minutes = int((time.time() - self._offline_since) / 60)
            return False, -1.0, offline_minutes
