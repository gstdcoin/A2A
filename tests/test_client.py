"""Basic unit tests for GSTDClient — no network calls, no secrets required."""
import sys
import os
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import requests
from nacl.signing import VerifyKey
from gstd_a2a.gstd_client import GSTDClient


class StubResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.data


class TestGSTDClientInit:
    def test_default_url(self):
        client = GSTDClient()
        assert client.api_url == 'https://app.gstdtoken.com'

    def test_custom_url_strips_trailing_slash(self):
        client = GSTDClient(api_url='https://app.gstdtoken.com/')
        assert client.api_url == 'https://app.gstdtoken.com'

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv('GSTD_API_KEY', 'test-key-123')
        client = GSTDClient()
        assert client.api_key == 'test-key-123'

    def test_api_key_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv('GSTD_API_KEY', 'env-key')
        client = GSTDClient(api_key='explicit-key')
        assert client.api_key == 'explicit-key'

    def test_wallet_address(self):
        client = GSTDClient(wallet_address='EQTest123')
        assert client.wallet_address == 'EQTest123'


class TestGSTDClientHeaders:
    def test_headers_include_content_type(self):
        client = GSTDClient()
        headers = client._get_headers()
        assert headers['Content-Type'] == 'application/json'

    def test_headers_include_api_key(self):
        client = GSTDClient(api_key='my-key')
        headers = client._get_headers()
        assert headers['Authorization'] == 'Bearer my-key'

    def test_headers_include_wallet(self):
        client = GSTDClient(wallet_address='EQtest')
        headers = client._get_headers()
        assert headers['X-Wallet-Address'] == 'EQtest'

    def test_headers_no_auth_without_key(self):
        client = GSTDClient(api_key=None)
        headers = client._get_headers()
        assert 'Authorization' not in headers


class TestGSTDClientTaskPayload:
    def test_node_id_set_after_register(self):
        client = GSTDClient()
        client.node_id = 'node-abc'
        assert client.node_id == 'node-abc'


class TestGSTDClientNodeIdentity:
    def test_identity_is_persistent_and_headers_prove_key_ownership(self, tmp_path):
        identity_path = tmp_path / 'node-ed25519.key'
        client = GSTDClient(wallet_address='EQtest', node_identity_path=identity_path)

        first = client._node_auth_headers('EQtest')
        second = client._node_auth_headers('EQtest')

        assert identity_path.exists()
        assert first['X-GSTD-Node-Id'] == 'EQtest'
        timestamp = first['X-GSTD-Node-Ts']
        message = hashlib.sha256(f"EQtest:{timestamp}".encode('utf-8')).digest()
        public_key = client._get_node_signing_key().verify_key.encode()
        VerifyKey(public_key).verify(message, bytes.fromhex(first['X-GSTD-Node-Sig']))
        second_message = hashlib.sha256(
            f"EQtest:{second['X-GSTD-Node-Ts']}".encode('utf-8')
        ).digest()
        VerifyKey(public_key).verify(second_message, bytes.fromhex(second['X-GSTD-Node-Sig']))

        restarted = GSTDClient(wallet_address='EQtest', node_identity_path=identity_path)
        assert restarted._get_node_signing_key().verify_key.encode() == public_key

    def test_registration_binds_the_persistent_public_key(self, monkeypatch, tmp_path):
        identity_path = tmp_path / 'node-ed25519.key'
        client = GSTDClient(wallet_address='EQtest', node_identity_path=identity_path)
        captured = {}

        def post(*args, **kwargs):
            captured.update(kwargs)
            return StubResponse(200, {'node_id': 'EQtest'})

        monkeypatch.setattr('gstd_a2a.gstd_client.requests.post', post)

        assert client.register_node()['node_id'] == 'EQtest'
        assert captured['json']['node_id'] == 'EQtest'
        assert captured['json']['node_pubkey'] == client._get_node_signing_key().verify_key.encode().hex()

    def test_registration_rejects_a_different_server_identity(self, monkeypatch, tmp_path):
        client = GSTDClient(wallet_address='EQtest', node_identity_path=tmp_path / 'node-ed25519.key')
        calls = []

        def post(*args, **kwargs):
            calls.append(1)
            return StubResponse(200, {'node_id': 'different-node'})

        monkeypatch.setattr('gstd_a2a.gstd_client.requests.post', post)

        with pytest.raises(RuntimeError, match='different from the signed identity'):
            client.register_node()
        assert len(calls) == 1
        assert client.node_id == 'EQtest'


class TestGSTDClientResponses:
    def test_pending_tasks_raises_on_server_error(self, monkeypatch):
        client = GSTDClient(wallet_address='EQtest')
        monkeypatch.setattr(
            'gstd_a2a.gstd_client.requests.get',
            lambda *args, **kwargs: StubResponse(503),
        )

        with pytest.raises(requests.HTTPError, match='503'):
            client.get_pending_tasks()

    def test_pending_tasks_reauthenticates_once(self, monkeypatch):
        client = GSTDClient(wallet_address='EQtest')
        client.node_id = 'node-1'
        responses = iter([StubResponse(401), StubResponse(200, {'tasks': [{'task_id': 'task-1'}]})])
        monkeypatch.setattr(
            'gstd_a2a.gstd_client.requests.get',
            lambda *args, **kwargs: next(responses),
        )
        monkeypatch.setattr(client, 'reauthenticate', lambda: True)

        assert client.get_pending_tasks() == [{'task_id': 'task-1'}]

    def test_pending_tasks_rejects_invalid_response_shape(self, monkeypatch):
        client = GSTDClient()
        monkeypatch.setattr(
            'gstd_a2a.gstd_client.requests.get',
            lambda *args, **kwargs: StubResponse(200, {'tasks': 'not-a-list'}),
        )

        with pytest.raises(ValueError, match='invalid response'):
            client.get_pending_tasks()

    def test_submit_result_raises_on_http_error_without_retry(self, monkeypatch):
        client = GSTDClient(wallet_address='EQtest')
        calls = []

        def post(*args, **kwargs):
            calls.append(1)
            return StubResponse(500)

        monkeypatch.setattr('gstd_a2a.gstd_client.requests.post', post)

        with pytest.raises(requests.HTTPError, match='500'):
            client.submit_result('task-1', {'ok': True})
        assert len(calls) == 1

    def test_heartbeat_reports_http_failure(self, monkeypatch):
        client = GSTDClient(wallet_address='EQtest')
        monkeypatch.setattr(
            'gstd_a2a.gstd_client.requests.post',
            lambda *args, **kwargs: StubResponse(503),
        )

        assert client.send_heartbeat() is False

    def test_heartbeat_reports_success(self, monkeypatch):
        client = GSTDClient(wallet_address='EQtest')
        monkeypatch.setattr(
            'gstd_a2a.gstd_client.requests.post',
            lambda *args, **kwargs: StubResponse(200),
        )

        assert client.send_heartbeat() is True
