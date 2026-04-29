"""`polyplace-verify` — shells out to `forge verify-contract` for all three contracts."""

import json
import subprocess
from pathlib import Path

import click
from eth_abi import encode

from polyplace_contracts.networks import get_network, resolve_verifier

# (sol_path, contract_name, constructor types) — values come from the manifest at runtime.
_CONTRACTS: tuple[tuple[str, str, list[str]], ...] = (
    ("src/PlaceToken.sol", "PlaceToken", []),
    (
        "src/PlaceFaucet.sol",
        "PlaceFaucet",
        ["address", "uint256", "uint256", "address"],
    ),
    (
        "src/PlaceGrid.sol",
        "PlaceGrid",
        ["address", "address", "uint256", "uint256", "address"],
    ),
)


def _ctor_values(name: str, manifest: dict) -> list:
    if name == "PlaceToken":
        return []
    if name == "PlaceFaucet":
        return [
            manifest["token"],
            int(manifest["claimAmount"]),
            int(manifest["cooldown"]),
            manifest["deployer"],
        ]
    if name == "PlaceGrid":
        return [
            manifest["token"],
            manifest["faucet"],
            int(manifest["rentPrice"]),
            int(manifest["rentDuration"]),
            manifest["deployer"],
        ]
    raise AssertionError(f"unknown contract {name!r}")


def _address(name: str, manifest: dict) -> str:
    return {
        "PlaceToken": manifest["token"],
        "PlaceFaucet": manifest["faucet"],
        "PlaceGrid": manifest["grid"],
    }[name]


@click.command()
@click.option(
    "--network",
    required=True,
    help="Named network from polyplace_contracts.networks (e.g. amoy, polygon).",
)
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Deployment manifest JSON written by polyplace-deploy.",
)
def main(network: str, manifest_path: Path) -> None:
    """Verify PlaceToken / PlaceFaucet / PlaceGrid on the chain's block explorer.

    Must be run from the contracts repo root: `forge verify-contract` recompiles
    from source to compare metadata hashes, so it needs `src/`, `foundry.toml`,
    and `lib/` reachable from the current working directory.

    Compiler version, optimizer runs, and EVM version come from `foundry.toml` —
    the same source of truth as the deploy build, so verify and deploy can never
    disagree.
    """
    try:
        chain_id = get_network(network).chain_id
        verifier_url, api_key = resolve_verifier(network)
    except (ValueError, RuntimeError) as exc:
        raise click.UsageError(str(exc)) from exc

    manifest = json.loads(manifest_path.read_text())

    for sol_path, contract_name, types in _CONTRACTS:
        address = _address(contract_name, manifest)
        values = _ctor_values(contract_name, manifest)
        argv = [
            "forge",
            "verify-contract",
            address,
            f"{sol_path}:{contract_name}",
            "--chain-id",
            str(chain_id),
            "--verifier-url",
            verifier_url,
            "--etherscan-api-key",
            api_key,
        ]
        if types:
            argv += ["--constructor-args", "0x" + encode(types, values).hex()]
        argv.append("--watch")

        click.echo(f"Verifying {contract_name} at {address}…")
        subprocess.run(argv, check=True)


if __name__ == "__main__":
    main()
