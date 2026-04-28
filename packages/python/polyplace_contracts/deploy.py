"""Pure-Python deployment of the Polyplace contract suite.

This module mirrors `script/Deploy.s.sol` but performs no I/O — it only
talks to the supplied `Web3` instance and signs with the supplied key. The
caller is responsible for reading any environment, writing manifests, etc.
"""

from dataclasses import dataclass, field
from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from polyplace_contracts import (
    INITIAL_SUPPLY,
    PLACE_FAUCET_ABI,
    PLACE_FAUCET_BYTECODE,
    PLACE_GRID_ABI,
    PLACE_GRID_BYTECODE,
    PLACE_TOKEN_ABI,
    PLACE_TOKEN_BYTECODE,
)


# Defaults match the constants in `script/Deploy.s.sol`.
_DEFAULT_CLAIM_AMOUNT = 100 * 10**18
_DEFAULT_COOLDOWN = 86_400
_DEFAULT_RENT_PRICE = 10 * 10**18
_DEFAULT_RENT_DURATION = 86_400


@dataclass(frozen=True)
class DeployParams:
    claim_amount: int = _DEFAULT_CLAIM_AMOUNT
    cooldown: int = _DEFAULT_COOLDOWN
    rent_price: int = _DEFAULT_RENT_PRICE
    rent_duration: int = _DEFAULT_RENT_DURATION


@dataclass(frozen=True)
class Deployment:
    chain_id: int
    deployer: str
    token: str
    faucet: str
    grid: str
    # Block in which `PlaceGrid` was deployed. Indexers backfilling grid
    # events should start here — earlier blocks cannot contain grid logs.
    start_block: int
    # Block of the final `token.transfer(faucet, INITIAL_SUPPLY)` call.
    deployed_at_block: int
    params: DeployParams
    tx_hashes: dict[str, str] = field(default_factory=dict)


def deploy(
    w3: Web3,
    deployer_key: str,
    params: DeployParams | None = None,
) -> Deployment:
    """Deploy PlaceToken, PlaceFaucet, PlaceGrid and seed the faucet.

    Pure: reads no environment variables and writes no files. Callers wire
    a configured `Web3` (with any required middleware already attached) and
    a hex private key; this function signs and broadcasts every transaction.
    """
    params = params or DeployParams()
    account: LocalAccount = Account.from_key(deployer_key)
    deployer = account.address
    chain_id = w3.eth.chain_id

    def _send(builder: Any) -> tuple[str, dict[str, Any]]:
        tx = builder.build_transaction({
            "from": deployer,
            "chainId": chain_id,
            "nonce": w3.eth.get_transaction_count(deployer),
        })
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise RuntimeError(f"Transaction {tx_hash.hex()} reverted")
        return tx_hash.hex(), receipt

    def _deploy(abi: list, bytecode: str, *args: Any) -> tuple[str, str, dict[str, Any]]:
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash, receipt = _send(contract.constructor(*args))
        return receipt.contractAddress, tx_hash, receipt

    token_addr, token_tx, _ = _deploy(PLACE_TOKEN_ABI, PLACE_TOKEN_BYTECODE)
    faucet_addr, faucet_tx, _ = _deploy(
        PLACE_FAUCET_ABI,
        PLACE_FAUCET_BYTECODE,
        token_addr,
        params.claim_amount,
        params.cooldown,
        deployer,
    )
    grid_addr, grid_tx, grid_receipt = _deploy(
        PLACE_GRID_ABI,
        PLACE_GRID_BYTECODE,
        token_addr,
        faucet_addr,
        params.rent_price,
        params.rent_duration,
        deployer,
    )

    token = w3.eth.contract(address=token_addr, abi=PLACE_TOKEN_ABI)
    transfer_tx, transfer_receipt = _send(token.functions.transfer(faucet_addr, INITIAL_SUPPLY))

    return Deployment(
        chain_id=chain_id,
        deployer=deployer,
        token=token_addr,
        faucet=faucet_addr,
        grid=grid_addr,
        start_block=grid_receipt.blockNumber,
        deployed_at_block=transfer_receipt.blockNumber,
        params=params,
        tx_hashes={
            "token": token_tx,
            "faucet": faucet_tx,
            "grid": grid_tx,
            "transfer": transfer_tx,
        },
    )


__all__ = ["DeployParams", "Deployment", "deploy"]
