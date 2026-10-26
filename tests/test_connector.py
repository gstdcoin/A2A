"""Standalone monitor must use signed identity and leave task queues untouched."""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("signed_connector", Path(__file__).parents[1] / "connect.py")
connector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(connector)


def test_connector_reuses_identity_and_normalizes_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("GSTD_NODE_IDENTITY_FILE", str(tmp_path / "identity"))
    a = connector.create_client("EQ_public", "https://example.test/api/v1/")
    b = connector.create_client("EQ_public", "https://example.test")
    assert a.api_url == "https://example.test"
    assert a.node_id == b.node_id
    assert a.node_id.startswith("a2a-py-")
    assert a._get_headers()["X-GSTD-Node-Sig"]
    monkeypatch.setenv("GSTD_NODE_IDENTITY_FILE", str(tmp_path / "other"))
    assert connector.create_client("EQ_public").node_id != a.node_id


def test_monitor_never_claims_tasks(monkeypatch):
    class Client:
        registered = False
        def register_node(self, **kwargs):
            self.registered = True
        def send_heartbeat(self):
            assert self.registered
            return True
        def get_pending_tasks(self):
            raise AssertionError("monitor must not claim work")
    client = Client()
    monkeypatch.setattr(connector, "create_client", lambda wallet: client)
    monkeypatch.setattr(sys, "argv", ["connect.py", "--wallet", "EQ_public"])
    def stop(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(connector.time, "sleep", stop)
    connector.main()
    assert client.registered
