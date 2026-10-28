"""Retired placeholder workers must stop before any network participation."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "swarm" / "swarm_client.py"

def load_legacy():
    spec = importlib.util.spec_from_file_location("retired_swarm", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_constructor_and_execution_fail_before_network(monkeypatch):
    module = load_legacy()
    def forbidden(*args, **kwargs):
        pytest.fail("retired client attempted network access")
    monkeypatch.setattr(module.requests, "get", forbidden)
    monkeypatch.setattr(module.requests, "post", forbidden)
    with pytest.raises(RuntimeError, match="retired"):
        module.SwarmClient(api_key="public-test-placeholder", wallet="public-test-placeholder")
    old_instance = object.__new__(module.SwarmClient)
    with pytest.raises(RuntimeError, match="retired"):
        old_instance._execute_task({"task_id": "test"})
    with pytest.raises(RuntimeError, match="retired"):
        old_instance.run()

def test_cli_exits_before_optional_dependencies_or_configuration():
    result = subprocess.run([sys.executable, str(SOURCE)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 2
    assert "Legacy swarm client is retired" in result.stderr
    assert "GSTD_API_KEY required" not in result.stderr
