"""`polyplace-deploy` — click-based CLI wrapping `polyplace_contracts.deploy.deploy`."""

import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import click
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from polyplace_contracts import INITIAL_SUPPLY
from polyplace_contracts.deploy import DeployParams, Deployment, deploy


def _build_manifest(d: Deployment, name: str | None, created_at: str) -> dict:
    manifest: dict = {
        "chainId": d.chain_id,
        "deployer": d.deployer,
        "token": d.token,
        "faucet": d.faucet,
        "grid": d.grid,
        "initialSupply": str(INITIAL_SUPPLY),
        "claimAmount": str(d.params.claim_amount),
        "cooldown": d.params.cooldown,
        "rentPrice": str(d.params.rent_price),
        "rentDuration": d.params.rent_duration,
        "startBlock": d.start_block,
        "createdAt": created_at,
        "txHashes": d.tx_hashes,
    }
    if name is not None:
        manifest["name"] = name
    return manifest


def _format_env_block(d: Deployment, rpc_url: str) -> str:
    return (
        f"export POLYPLACE_RPC_URL={rpc_url}\n"
        f"export POLYPLACE_TOKEN_ADDRESS={d.token}\n"
        f"export POLYPLACE_FAUCET_ADDRESS={d.faucet}\n"
        f"export POLYPLACE_GRID_ADDRESS={d.grid}\n"
        f"export POLYPLACE_START_BLOCK={d.start_block}\n"
    )


@click.command()
@click.option("--rpc-url", required=True, help="JSON-RPC endpoint to deploy against.")
@click.option(
    "--private-key",
    required=True,
    envvar="POLYPLACE_PRIVATE_KEY",
    help="Deployer private key (falls back to POLYPLACE_PRIVATE_KEY).",
)
@click.option(
    "--manifest-out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write deployment manifest JSON to this path.",
)
@click.option(
    "--env-out",
    default=None,
    help="Write shell env block to this path (use '-' for stdout).",
)
@click.option("--name", default=None, help="Optional human label, written into the manifest.")
@click.option("--claim-amount", type=int, default=None, help="Faucet claim amount (token base units).")
@click.option("--cooldown", type=int, default=None, help="Faucet cooldown (seconds).")
@click.option("--rent-price", type=int, default=None, help="Cell rent price (token base units).")
@click.option("--rent-duration", type=int, default=None, help="Cell rent duration (seconds).")
def main(
    rpc_url: str,
    private_key: str,
    manifest_out: Path | None,
    env_out: str | None,
    name: str | None,
    claim_amount: int | None,
    cooldown: int | None,
    rent_price: int | None,
    rent_duration: int | None,
) -> None:
    """Deploy PlaceToken / PlaceFaucet / PlaceGrid and seed the faucet.

    By default the shell env block is written to stdout. To load it into
    your current shell:

    \b
        eval "$(polyplace-deploy --rpc-url ... --private-key ...)"
        # or
        source <(polyplace-deploy --rpc-url ... --private-key ...)

    Pass --env-out PATH to write the block to a file instead.
    """
    overrides = {
        k: v
        for k, v in {
            "claim_amount": claim_amount,
            "cooldown": cooldown,
            "rent_price": rent_price,
            "rent_duration": rent_duration,
        }.items()
        if v is not None
    }
    params = replace(DeployParams(), **overrides)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise click.ClickException(f"Cannot connect to RPC at {rpc_url}")
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    deployment = deploy(w3, private_key, params)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if manifest_out is not None:
        manifest = _build_manifest(deployment, name, created_at)
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest_out.write_text(json.dumps(manifest, indent=2) + "\n")

    env_block = _format_env_block(deployment, rpc_url)
    if env_out is None or env_out == "-":
        sys.stdout.write(env_block)
    else:
        env_path = Path(env_out)
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(env_block)


if __name__ == "__main__":
    main()
