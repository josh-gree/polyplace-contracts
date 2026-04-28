"""End-to-end deploy tests against a local Anvil chain."""

import os
import re
from pathlib import Path

import pytest
from click.testing import CliRunner
from web3 import Web3

from polyplace_contracts import (
    INITIAL_SUPPLY,
    PLACE_FAUCET_ABI,
    PLACE_GRID_ABI,
    PLACE_TOKEN_ABI,
)
from polyplace_contracts.cli.deploy import main as deploy_cli
from polyplace_contracts.deploy import DeployParams, deploy

from conftest import AnvilNode


def _w3(node: AnvilNode) -> Web3:
    return Web3(Web3.HTTPProvider(node.rpc_url))


def test_deploy_returns_three_addresses(anvil: AnvilNode) -> None:
    w3 = _w3(anvil)

    deployment = deploy(w3, anvil.deployer_key)

    for addr in (deployment.token, deployment.faucet, deployment.grid):
        assert w3.eth.get_code(addr) != b"", f"no code at {addr}"


def test_faucet_holds_initial_supply(anvil: AnvilNode) -> None:
    w3 = _w3(anvil)

    deployment = deploy(w3, anvil.deployer_key)

    token = w3.eth.contract(address=deployment.token, abi=PLACE_TOKEN_ABI)
    assert token.functions.balanceOf(deployment.faucet).call() == INITIAL_SUPPLY
    assert token.functions.totalSupply().call() == INITIAL_SUPPLY


def test_params_passed_through(anvil: AnvilNode) -> None:
    w3 = _w3(anvil)
    custom = DeployParams(
        claim_amount=42 * 10**18,
        cooldown=3600,
        rent_price=7 * 10**18,
        rent_duration=7200,
    )

    deployment = deploy(w3, anvil.deployer_key, custom)

    faucet = w3.eth.contract(address=deployment.faucet, abi=PLACE_FAUCET_ABI)
    grid = w3.eth.contract(address=deployment.grid, abi=PLACE_GRID_ABI)
    assert faucet.functions.claimAmount().call() == custom.claim_amount
    assert faucet.functions.cooldown().call() == custom.cooldown
    assert grid.functions.rentPrice().call() == custom.rent_price
    assert grid.functions.rentDuration().call() == custom.rent_duration
    assert deployment.params == custom


def test_start_block_is_grid_deploy_block(anvil: AnvilNode) -> None:
    w3 = _w3(anvil)

    deployment = deploy(w3, anvil.deployer_key)

    grid_tx_hash = deployment.tx_hashes["grid"]
    grid_receipt = w3.eth.get_transaction_receipt(grid_tx_hash)
    assert deployment.start_block == grid_receipt.blockNumber


def test_deploy_is_pure(anvil: AnvilNode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for var in [
        "POLYPLACE_RPC_URL",
        "POLYPLACE_TOKEN_ADDRESS",
        "POLYPLACE_FAUCET_ADDRESS",
        "POLYPLACE_GRID_ADDRESS",
        "POLYPLACE_PRIVATE_KEY",
        "POLYPLACE_DEPLOYMENT_MANIFEST_PATH",
        "PRIVATE_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)
    before = set(os.listdir(tmp_path))

    deploy(_w3(anvil), anvil.deployer_key)

    assert set(os.listdir(tmp_path)) == before


def test_cli_prints_env_block_to_stdout(anvil: AnvilNode) -> None:
    runner = CliRunner()

    result = runner.invoke(
        deploy_cli,
        [
            "--rpc-url",
            anvil.rpc_url,
            "--private-key",
            anvil.deployer_key,
            "--env-out",
            "-",
        ],
    )

    assert result.exit_code == 0, result.output
    env = dict(re.findall(r"^export (\w+)=(\S+)$", result.output, flags=re.MULTILINE))
    assert env["POLYPLACE_RPC_URL"] == anvil.rpc_url
    for key in (
        "POLYPLACE_TOKEN_ADDRESS",
        "POLYPLACE_FAUCET_ADDRESS",
        "POLYPLACE_GRID_ADDRESS",
        "POLYPLACE_START_BLOCK",
    ):
        assert key in env, f"missing {key} in CLI output"
    w3 = _w3(anvil)
    for key in ("POLYPLACE_TOKEN_ADDRESS", "POLYPLACE_FAUCET_ADDRESS", "POLYPLACE_GRID_ADDRESS"):
        assert w3.eth.get_code(env[key]) != b""


def test_cli_writes_manifest(anvil: AnvilNode, tmp_path: Path) -> None:
    runner = CliRunner()
    manifest_path = tmp_path / "out" / "local.json"

    result = runner.invoke(
        deploy_cli,
        [
            "--rpc-url",
            anvil.rpc_url,
            "--private-key",
            anvil.deployer_key,
            "--manifest-out",
            str(manifest_path),
            "--name",
            "anvil-test",
            "--rent-price",
            str(5 * 10**18),
        ],
    )

    assert result.exit_code == 0, result.output
    import json

    manifest = json.loads(manifest_path.read_text())
    assert manifest["chainId"] == 31337
    assert manifest["name"] == "anvil-test"
    assert manifest["rentPrice"] == str(5 * 10**18)
    assert manifest["initialSupply"] == str(INITIAL_SUPPLY)
    for key in ("token", "faucet", "grid", "deployer", "startBlock", "createdAt", "txHashes"):
        assert key in manifest, f"manifest missing {key}"
    assert set(manifest["txHashes"]) == {"token", "faucet", "grid", "transfer"}
