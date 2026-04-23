"""Top-level Cli class exposed via python-fire as `polyplace-dev`.

All configuration is read from environment variables — see `config.py`.
There are no defaults: required values raise a clear error when absent.
"""

from __future__ import annotations

import os
import sys

import fire
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.exceptions import ContractLogicError
from web3.middleware import ExtraDataToPOAMiddleware

from .config import (
    get_faucet_address,
    get_grid_address,
    get_rpc_url,
    get_token_address,
)
from .wrappers import Faucet, Grid, Token
from polyplace_contracts.errors import PolyplaceContractError


class Cli:
    """polyplace-dev: a CLI for interacting with the PolyPlace contracts."""

    def __init__(self) -> None:
        self.__w3: Web3 | None = None
        self.__account: LocalAccount | None = None
        self.__account_loaded = False

    def _w3(self) -> Web3:
        if self.__w3 is None:
            rpc_url = get_rpc_url()
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not w3.is_connected():
                raise RuntimeError(f"Cannot connect to RPC at {rpc_url}")
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            self.__w3 = w3
        return self.__w3

    def _account(self) -> LocalAccount | None:
        if not self.__account_loaded:
            key = os.environ.get("POLYPLACE_PRIVATE_KEY")
            if key:
                self.__account = self._w3().eth.account.from_key(key)
            self.__account_loaded = True
        return self.__account

    @property
    def faucet(self) -> Faucet:
        return Faucet(self._w3(), get_faucet_address(), self._account())

    @property
    def token(self) -> Token:
        return Token(self._w3(), get_token_address(), self._account())

    @property
    def grid(self) -> Grid:
        return Grid(self._w3(), get_grid_address(), self._account())


def main() -> None:
    try:
        fire.Fire(Cli)
    except PolyplaceContractError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    except ContractLogicError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
