from __future__ import annotations

import os
from dataclasses import dataclass

from web3 import Web3
from web3.types import TxReceipt

from . import (
    PLACE_TOKEN_ABI,
    PLACE_TOKEN_BYTECODE,
    PLACE_FAUCET_ABI,
    PLACE_FAUCET_BYTECODE,
    PLACE_GRID_ABI,
    PLACE_GRID_BYTECODE,
)

INITIAL_SUPPLY       = 1_000_000_000 * 10**18
DEPLOY_CLAIM_AMOUNT  = 100 * 10**18
DEPLOY_COOLDOWN      = 86400       # 1 day
DEPLOY_RENT_PRICE    = 10 * 10**18
DEPLOY_RENT_DURATION = 86400       # 1 day


@dataclass
class Deployment:
    token:  str
    faucet: str
    grid:   str


def deploy(
    w3: Web3,
    deployer_key: str,
    claim_amount:  int = DEPLOY_CLAIM_AMOUNT,
    cooldown:      int = DEPLOY_COOLDOWN,
    rent_price:    int = DEPLOY_RENT_PRICE,
    rent_duration: int = DEPLOY_RENT_DURATION,
) -> Deployment:
    """Deploy PlaceToken, PlaceFaucet and PlaceGrid, transfer full supply to faucet."""
    account = w3.eth.account.from_key(deployer_key)

    def _deploy(abi, bytecode, *args) -> str:
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        tx = contract.constructor(*args).build_transaction({
            "from":  account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
        })
        receipt = _send(tx)
        return receipt.contractAddress

    def _send(tx: dict) -> TxReceipt:
        signed   = account.sign_transaction(tx)
        tx_hash  = w3.eth.send_raw_transaction(signed.raw_transaction)
        return w3.eth.wait_for_transaction_receipt(tx_hash)

    token_address  = _deploy(PLACE_TOKEN_ABI,  PLACE_TOKEN_BYTECODE)
    faucet_address = _deploy(PLACE_FAUCET_ABI, PLACE_FAUCET_BYTECODE,
                             token_address, claim_amount, cooldown, account.address)
    grid_address   = _deploy(PLACE_GRID_ABI,   PLACE_GRID_BYTECODE,
                             token_address, faucet_address, rent_price, rent_duration, account.address)

    # Transfer full supply to faucet
    token = w3.eth.contract(address=token_address, abi=PLACE_TOKEN_ABI)
    tx = token.functions.transfer(faucet_address, INITIAL_SUPPLY).build_transaction({
        "from":  account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
    })
    _send(tx)

    return Deployment(token=token_address, faucet=faucet_address, grid=grid_address)


def load_deployment() -> Deployment:
    """Load deployment addresses from environment variables.

    Expected env vars:
        PLACE_TOKEN_ADDRESS
        PLACE_FAUCET_ADDRESS
        PLACE_GRID_ADDRESS
    """
    return Deployment(
        token=os.environ["PLACE_TOKEN_ADDRESS"],
        faucet=os.environ["PLACE_FAUCET_ADDRESS"],
        grid=os.environ["PLACE_GRID_ADDRESS"],
    )
