"""Unit tests for `polyplace-verify` — patches `subprocess.run`, no real explorer."""

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from eth_abi import encode

from polyplace_contracts.cli.verify import main as verify_cli

CLAIM_AMOUNT = 150 * 10**18
COOLDOWN = 24 * 60 * 60
RENT_PRICE = 1 * 10**18
RENT_DURATION = 7 * 24 * 60 * 60

DEPLOYER = "0x" + "11" * 20
TOKEN = "0x" + "22" * 20
FAUCET = "0x" + "33" * 20
GRID = "0x" + "44" * 20

AMOY_VERIFIER_URL = "https://api-amoy.polygonscan.com/api"
API_KEY = "test-polygonscan-key"


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "chainId": 80002,
                "deployer": DEPLOYER,
                "token": TOKEN,
                "faucet": FAUCET,
                "grid": GRID,
                "claimAmount": str(CLAIM_AMOUNT),
                "cooldown": COOLDOWN,
                "rentPrice": str(RENT_PRICE),
                "rentDuration": RENT_DURATION,
            }
        )
    )


def _set_amoy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLYGONSCAN_API_KEY", API_KEY)


def _run(monkeypatch: pytest.MonkeyPatch, manifest_path: Path) -> tuple[list[list[str]], object]:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], check: bool = False, **kwargs: object) -> object:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CliRunner()
    result = runner.invoke(
        verify_cli,
        ["--network", "amoy", "--manifest", str(manifest_path)],
        catch_exceptions=False,
    )
    return calls, result


def test_verify_invokes_forge_three_times_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_amoy_env(monkeypatch)
    manifest = tmp_path / "amoy.json"
    _write_manifest(manifest)

    calls, result = _run(monkeypatch, manifest)

    assert result.exit_code == 0, result.output
    assert len(calls) == 3
    assert [c[3] for c in calls] == [
        "src/PlaceToken.sol:PlaceToken",
        "src/PlaceFaucet.sol:PlaceFaucet",
        "src/PlaceGrid.sol:PlaceGrid",
    ]
    assert [c[2] for c in calls] == [TOKEN, FAUCET, GRID]


def test_verify_passes_chain_and_verifier_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_amoy_env(monkeypatch)
    manifest = tmp_path / "amoy.json"
    _write_manifest(manifest)

    calls, result = _run(monkeypatch, manifest)

    assert result.exit_code == 0, result.output
    for argv in calls:
        assert argv[0] == "forge"
        assert argv[1] == "verify-contract"
        assert argv[argv.index("--chain-id") + 1] == "80002"
        assert argv[argv.index("--verifier-url") + 1] == AMOY_VERIFIER_URL
        assert argv[argv.index("--etherscan-api-key") + 1] == API_KEY
        assert "--watch" in argv


def test_placetoken_omits_constructor_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_amoy_env(monkeypatch)
    manifest = tmp_path / "amoy.json"
    _write_manifest(manifest)

    calls, result = _run(monkeypatch, manifest)

    assert result.exit_code == 0, result.output
    token_argv = calls[0]
    assert "--constructor-args" not in token_argv


def test_faucet_constructor_args_match_eth_abi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_amoy_env(monkeypatch)
    manifest = tmp_path / "amoy.json"
    _write_manifest(manifest)

    calls, _ = _run(monkeypatch, manifest)

    faucet_argv = calls[1]
    args_hex = faucet_argv[faucet_argv.index("--constructor-args") + 1]
    expected = (
        "0x"
        + encode(
            ["address", "uint256", "uint256", "address"],
            [TOKEN, CLAIM_AMOUNT, COOLDOWN, DEPLOYER],
        ).hex()
    )
    assert args_hex == expected


def test_grid_constructor_args_match_eth_abi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_amoy_env(monkeypatch)
    manifest = tmp_path / "amoy.json"
    _write_manifest(manifest)

    calls, _ = _run(monkeypatch, manifest)

    grid_argv = calls[2]
    args_hex = grid_argv[grid_argv.index("--constructor-args") + 1]
    expected = (
        "0x"
        + encode(
            ["address", "address", "uint256", "uint256", "address"],
            [TOKEN, FAUCET, RENT_PRICE, RENT_DURATION, DEPLOYER],
        ).hex()
    )
    assert args_hex == expected


def test_called_process_error_propagates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_amoy_env(monkeypatch)
    manifest = tmp_path / "amoy.json"
    _write_manifest(manifest)

    def fake_run(argv: list[str], check: bool = False, **kwargs: object) -> object:
        raise subprocess.CalledProcessError(returncode=1, cmd=argv)

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CliRunner()
    result = runner.invoke(
        verify_cli,
        ["--network", "amoy", "--manifest", str(manifest)],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, subprocess.CalledProcessError)


def test_unknown_network_raises_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_amoy_env(monkeypatch)
    manifest = tmp_path / "amoy.json"
    _write_manifest(manifest)

    runner = CliRunner()
    result = runner.invoke(
        verify_cli,
        ["--network", "nonsense", "--manifest", str(manifest)],
    )

    assert result.exit_code != 0
    assert "unknown network" in result.output.lower()


def test_missing_manifest_path_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_amoy_env(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(
        verify_cli,
        ["--network", "amoy", "--manifest", "/no/such/file.json"],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_localhost_has_no_verifier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "local.json"
    _write_manifest(manifest)

    runner = CliRunner()
    result = runner.invoke(
        verify_cli,
        ["--network", "localhost", "--manifest", str(manifest)],
    )

    assert result.exit_code != 0
    assert "no verifier" in result.output.lower()
