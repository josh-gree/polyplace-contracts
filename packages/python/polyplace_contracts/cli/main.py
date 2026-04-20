"""Top-level Cli class exposed via python-fire as `polyplace-dev`.

All configuration is read from environment variables — see `config.py`.
There are no defaults: required values raise a clear error when absent.
"""

from __future__ import annotations

import json
import os

import fire
from eth_account.signers.local import LocalAccount
from web3 import Web3

from ..deploy import (
    DEPLOY_CLAIM_AMOUNT,
    DEPLOY_COOLDOWN,
    DEPLOY_RENT_DURATION,
    DEPLOY_RENT_PRICE,
)
from ..deploy import deploy as _deploy
from .config import (
    get_faucet_address,
    get_grid_address,
    get_private_key,
    get_rpc_url,
    get_token_address,
)
from .wrappers import Faucet, Grid, Token


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

    def deploy(
        self,
        claim_amount: int = DEPLOY_CLAIM_AMOUNT,
        cooldown: int = DEPLOY_COOLDOWN,
        rent_price: int = DEPLOY_RENT_PRICE,
        rent_duration: int = DEPLOY_RENT_DURATION,
    ) -> None:
        """Deploy PlaceToken, PlaceFaucet, PlaceGrid; print {token,faucet,grid} as JSON."""
        key = get_private_key()
        result = _deploy(
            self._w3(),
            key,
            claim_amount=claim_amount,
            cooldown=cooldown,
            rent_price=rent_price,
            rent_duration=rent_duration,
        )
        print(json.dumps({
            "token": result.token,
            "faucet": result.faucet,
            "grid": result.grid,
        }))


def main() -> None:
    fire.Fire(Cli)


if __name__ == "__main__":
    main()
