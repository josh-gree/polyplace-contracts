"""Env-var driven configuration for the polyplace CLI.

Every value must come from an environment variable. There are no defaults and
no file-based fallbacks: callers are responsible for setting these before
invoking the CLI.
"""

from __future__ import annotations

import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def get_rpc_url() -> str:
    return _require("POLYPLACE_RPC_URL")


def get_private_key() -> str:
    return _require("POLYPLACE_PRIVATE_KEY")


def get_token_address() -> str:
    return _require("POLYPLACE_TOKEN_ADDRESS")


def get_faucet_address() -> str:
    return _require("POLYPLACE_FAUCET_ADDRESS")


def get_grid_address() -> str:
    return _require("POLYPLACE_GRID_ADDRESS")
