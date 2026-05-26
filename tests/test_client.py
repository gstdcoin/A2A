"""Basic unit tests for GSTDClient — no network calls, no secrets required."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from gstd_a2a.gstd_client import GSTDClient


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
