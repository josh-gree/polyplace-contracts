"""Tests for `polyplace_contracts.networks`."""

import pytest

from polyplace_contracts.networks import (
    NETWORKS,
    get_network,
    resolve_rpc,
    resolve_verifier,
)


def test_networks_has_expected_keys() -> None:
    assert set(NETWORKS) == {"localhost", "amoy", "polygon"}


def test_get_network_returns_chain_id() -> None:
    assert get_network("amoy").chain_id == 80002
    assert get_network("polygon").chain_id == 137
    assert get_network("localhost").chain_id == 31337


def test_get_network_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown network"):
        get_network("nonsense")


def test_resolve_rpc_localhost_uses_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMOY_RPC_URL", raising=False)
    assert resolve_rpc("localhost") == "http://localhost:8545"


def test_resolve_rpc_amoy_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMOY_RPC_URL", "https://amoy.example/rpc")
    assert resolve_rpc("amoy") == "https://amoy.example/rpc"


def test_resolve_rpc_amoy_missing_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMOY_RPC_URL", raising=False)
    with pytest.raises(RuntimeError, match="AMOY_RPC_URL"):
        resolve_rpc("amoy")


def test_resolve_rpc_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown network"):
        resolve_rpc("nonsense")


def test_resolve_verifier_amoy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLYGONSCAN_API_KEY", "secret-key")
    url, key = resolve_verifier("amoy")
    assert url == "https://api-amoy.polygonscan.com/api"
    assert key == "secret-key"


def test_resolve_verifier_polygon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLYGONSCAN_API_KEY", "secret-key")
    url, key = resolve_verifier("polygon")
    assert url == "https://api.polygonscan.com/api"
    assert key == "secret-key"


def test_resolve_verifier_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POLYGONSCAN_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="POLYGONSCAN_API_KEY"):
        resolve_verifier("amoy")


def test_resolve_verifier_localhost_raises() -> None:
    with pytest.raises(ValueError, match="no verifier"):
        resolve_verifier("localhost")
