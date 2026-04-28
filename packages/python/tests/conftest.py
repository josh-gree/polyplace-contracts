"""Shared fixtures: spin up a local Anvil chain for tests that need a real EVM."""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from web3 import Web3


# anvil's first default funded account; private key matches the canonical
# `anvil --accounts 10` mnemonic. Fine for tests; never use in production.
ANVIL_DEFAULT_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


@dataclass(frozen=True)
class AnvilNode:
    rpc_url: str
    deployer_key: str


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_rpc(url: str, timeout: float = 10.0) -> None:
    w3 = Web3(Web3.HTTPProvider(url))
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if w3.is_connected():
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"Anvil never became reachable at {url}")


@pytest.fixture
def anvil() -> Iterator[AnvilNode]:
    port = _free_port()
    proc = subprocess.Popen(
        ["anvil", "--port", str(port), "--silent"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}"
        _wait_for_rpc(url)
        yield AnvilNode(rpc_url=url, deployer_key=ANVIL_DEFAULT_KEY)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
