"""Single source of truth for chain metadata used by the Python CLIs."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Network:
    name: str
    chain_id: int
    rpc_url: str | None
    rpc_env: str | None
    verifier_url: str | None
    verifier_key_env: str | None


NETWORKS: dict[str, Network] = {
    "localhost": Network(
        name="localhost",
        chain_id=31337,
        rpc_url="http://localhost:8545",
        rpc_env=None,
        verifier_url=None,
        verifier_key_env=None,
    ),
    "amoy": Network(
        name="amoy",
        chain_id=80002,
        rpc_url=None,
        rpc_env="AMOY_RPC_URL",
        verifier_url="https://api-amoy.polygonscan.com/api",
        verifier_key_env="POLYGONSCAN_API_KEY",
    ),
    "polygon": Network(
        name="polygon",
        chain_id=137,
        rpc_url=None,
        rpc_env="POLYGON_RPC_URL",
        verifier_url="https://api.polygonscan.com/api",
        verifier_key_env="POLYGONSCAN_API_KEY",
    ),
}


def get_network(name: str) -> Network:
    try:
        return NETWORKS[name]
    except KeyError:
        known = ", ".join(sorted(NETWORKS))
        raise ValueError(f"unknown network {name!r}; known: {known}") from None


def resolve_rpc(name: str) -> str:
    net = get_network(name)
    if net.rpc_url is not None:
        return net.rpc_url
    assert net.rpc_env is not None, f"network {name!r} has neither rpc_url nor rpc_env"
    value = os.environ.get(net.rpc_env)
    if not value:
        raise RuntimeError(f"network {name!r} requires env var {net.rpc_env} to be set")
    return value


def resolve_verifier(name: str) -> tuple[str, str]:
    net = get_network(name)
    if net.verifier_url is None or net.verifier_key_env is None:
        raise ValueError(f"network {name!r} has no verifier configured")
    key = os.environ.get(net.verifier_key_env)
    if not key:
        raise RuntimeError(f"network {name!r} requires env var {net.verifier_key_env} to be set")
    return net.verifier_url, key
