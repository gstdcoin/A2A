import os

import pytest

from gstd_a2a.gstd_wallet import GSTDWallet


def test_public_identity_does_not_expose_recovery_phrase():
    wallet = GSTDWallet()

    identity = wallet.get_identity()

    assert identity["address"] == wallet.address
    assert "mnemonic" not in identity
    assert len(wallet.export_mnemonic().split()) >= 12


def test_wallet_save_is_private_and_loads_round_trip(tmp_path):
    wallet = GSTDWallet()
    wallet_path = tmp_path / "nested" / "wallet.json"

    wallet.save(str(wallet_path))

    assert GSTDWallet.load(str(wallet_path)).address == wallet.address
    if os.name != "nt":
        assert wallet_path.stat().st_mode & 0o077 == 0


def test_wallet_load_rejects_file_without_recovery_phrase(tmp_path):
    wallet_path = tmp_path / "wallet.json"
    wallet_path.write_text('{"address":"EQtest"}', encoding="utf-8")

    with pytest.raises(ValueError, match="does not contain a recovery phrase"):
        GSTDWallet.load(str(wallet_path))
