import json
from pathlib import Path

from .errors import PolyplaceContractError

_artifacts_dir = Path(__file__).parent / "artifacts"


def _load(name: str) -> dict:
    with open(_artifacts_dir / f"{name}.json") as f:
        return json.load(f)


_token  = _load("PlaceToken")
_faucet = _load("PlaceFaucet")
_grid   = _load("PlaceGrid")

PLACE_TOKEN_ABI       = _token["abi"]
PLACE_TOKEN_BYTECODE  = _token["bytecode"]

PLACE_FAUCET_ABI      = _faucet["abi"]
PLACE_FAUCET_BYTECODE = _faucet["bytecode"]

PLACE_GRID_ABI        = _grid["abi"]
PLACE_GRID_BYTECODE   = _grid["bytecode"]

__all__ = [
    "PLACE_TOKEN_ABI",
    "PLACE_TOKEN_BYTECODE",
    "PLACE_FAUCET_ABI",
    "PLACE_FAUCET_BYTECODE",
    "PLACE_GRID_ABI",
    "PLACE_GRID_BYTECODE",
    "PolyplaceContractError",
]
