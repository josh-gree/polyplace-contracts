"""Decode Polyplace contract reverts into readable user-facing errors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from eth_utils import keccak
from web3 import Web3
from web3.exceptions import ContractCustomError, ContractLogicError

_ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
_GRID_SIZE = 1000
_PLACE_DECIMALS = Decimal(10) ** 18


class PolyplaceContractError(RuntimeError):
    """Readable contract failure raised by the Python client."""

    def __init__(
        self,
        message: str,
        *,
        error_name: str | None = None,
        data: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_name = error_name
        self.data = data


@dataclass(frozen=True)
class DecodedContractError:
    name: str
    arguments: tuple[tuple[str, Any], ...]
    data: str


def translate_contract_error(exc: ContractLogicError) -> PolyplaceContractError:
    data = extract_contract_error_data(exc)
    decoded = decode_contract_error_data(data) if data else None

    if decoded is not None:
        return PolyplaceContractError(
            format_decoded_contract_error(decoded),
            error_name=decoded.name,
            data=decoded.data,
        )

    if isinstance(exc, ContractCustomError) and data is not None:
        selector = data[:10]
        return PolyplaceContractError(
            f"Contract reverted with an unknown custom error (selector {selector}).",
            data=data,
        )

    message = _clean_contract_logic_message(str(exc))
    if not message:
        message = "Contract reverted."

    return PolyplaceContractError(message, data=data)


def extract_contract_error_data(exc: BaseException) -> str | None:
    candidates = [getattr(exc, "data", None), exc.args]
    for candidate in candidates:
        data = _find_hex_data(candidate)
        if data is not None:
            return data
    return None


def decode_contract_error_data(data: str) -> DecodedContractError | None:
    normalized = _find_hex_data(data)
    if normalized is None or len(normalized) < 10:
        return None

    item = _error_registry().get(normalized[2:10])
    if item is None:
        return None

    inputs = item.get("inputs", [])
    try:
        payload = bytes.fromhex(normalized[10:])
        decoded_values = tuple(_codec().decode([arg["type"] for arg in inputs], payload)) if inputs else ()
    except Exception:
        return None

    arguments: list[tuple[str, Any]] = []
    for index, (arg, value) in enumerate(zip(inputs, decoded_values)):
        name = arg.get("name") or f"arg{index}"
        arguments.append((name, _normalize_decoded_value(value)))

    return DecodedContractError(
        name=item["name"],
        arguments=tuple(arguments),
        data=normalized,
    )


def format_decoded_contract_error(error: DecodedContractError) -> str:
    args = dict(error.arguments)
    formatter = _ERROR_FORMATTERS.get(error.name)
    if formatter is not None:
        return formatter(args)

    if error.arguments:
        rendered = ", ".join(f"{name}={_format_value(value)}" for name, value in error.arguments)
        return f"{error.name}: {rendered}"

    return error.name


def _clean_contract_logic_message(message: str) -> str:
    prefixes = [
        "execution reverted: ",
        "execution reverted",
    ]
    for prefix in prefixes:
        if message.startswith(prefix):
            return message[len(prefix):].strip() or "Contract reverted."
    return message


def _find_hex_data(value: object) -> str | None:
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate.startswith("0x") and len(candidate) >= 10 and len(candidate) % 2 == 0:
            try:
                bytes.fromhex(candidate[2:])
            except ValueError:
                return None
            return candidate
        return None

    if isinstance(value, dict):
        for key in ("data", "result"):
            data = _find_hex_data(value.get(key))
            if data is not None:
                return data
        for nested in value.values():
            data = _find_hex_data(nested)
            if data is not None:
                return data
        return None

    if isinstance(value, (list, tuple)):
        for nested in value:
            data = _find_hex_data(nested)
            if data is not None:
                return data

    return None


def _normalize_decoded_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, list):
        return [_normalize_decoded_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_decoded_value(item) for item in value)
    return value


@lru_cache(maxsize=1)
def _codec():
    return Web3().codec


@lru_cache(maxsize=1)
def _error_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for contract_name in ("PlaceToken", "PlaceFaucet", "PlaceGrid"):
        for item in _load_abi(contract_name):
            if item.get("type") != "error":
                continue
            selector = keccak(text=_error_signature(item))[:4].hex()
            registry.setdefault(selector, item)
    return registry


def _load_abi(name: str) -> list[dict[str, Any]]:
    with open(_ARTIFACTS_DIR / f"{name}.json") as f:
        return json.load(f)["abi"]


def _error_signature(item: dict[str, Any]) -> str:
    arg_types = ",".join(arg["type"] for arg in item.get("inputs", []))
    return f"{item['name']}({arg_types})"


def _format_timestamp(timestamp: int) -> str:
    try:
        dt = datetime.fromtimestamp(timestamp, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return str(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%SZ")


def _format_place(amount: int) -> str:
    place = Decimal(amount) / _PLACE_DECIMALS
    text = format(place.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if not text:
        text = "0"
    return f"{text} PLACE ({amount} wei)"


def _format_value(value: Any) -> str:
    if isinstance(value, str) and value.startswith("0x") and len(value) == 42:
        try:
            return Web3.to_checksum_address(value)
        except ValueError:
            return value
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(_format_value(item) for item in value) + ")"
    return str(value)


def _format_cell(cell_id: int) -> str:
    x = cell_id % _GRID_SIZE
    y = cell_id // _GRID_SIZE
    return f"cell {cell_id} (x={x}, y={y})"


def _format_out_of_bounds(args: dict[str, Any]) -> str:
    return (
        f"Cell coordinates out of bounds: x={args['x']}, y={args['y']}. "
        f"Valid range is 0-{_GRID_SIZE - 1}."
    )


def _format_cell_not_available(args: dict[str, Any]) -> str:
    return (
        f"{_format_cell(args['cellId'])} is already rented until "
        f"{_format_timestamp(args['expiresAt'])}."
    )


def _format_not_cell_renter(args: dict[str, Any]) -> str:
    return (
        f"You do not currently rent {_format_cell(args['cellId'])}, or its rental has expired."
    )


def _format_invalid_rent_price(_: dict[str, Any]) -> str:
    return "Rent price must be greater than zero."


def _format_invalid_rent_duration(_: dict[str, Any]) -> str:
    return "Rent duration must be greater than zero."


def _format_too_many_cells(args: dict[str, Any]) -> str:
    return f"Too many cells in one request: {args['count']}. Maximum is 100."


def _format_array_length_mismatch(_: dict[str, Any]) -> str:
    return "The xs, ys, and colors lists must all be the same length."


def _format_cooldown(args: dict[str, Any]) -> str:
    return (
        "Faucet cooldown has not elapsed. "
        f"You can claim again at {_format_timestamp(args['availableAt'])}."
    )


def _format_insufficient_faucet_balance(args: dict[str, Any]) -> str:
    return (
        "Faucet balance is too low: "
        f"available {_format_place(args['available'])}, "
        f"required {_format_place(args['required'])}."
    )


def _format_ownable_invalid_owner(args: dict[str, Any]) -> str:
    return f"Invalid owner address: {_format_value(args['owner'])}."


def _format_ownable_unauthorized(args: dict[str, Any]) -> str:
    return f"Account {_format_value(args['account'])} is not authorized to perform this action."


def _format_safe_erc20_failed(args: dict[str, Any]) -> str:
    return f"The ERC20 operation failed for token {_format_value(args['token'])}."


def _format_erc20_insufficient_allowance(args: dict[str, Any]) -> str:
    return (
        "Token allowance is too low for "
        f"{_format_value(args['spender'])}: allowance {_format_place(args['allowance'])}, "
        f"required {_format_place(args['needed'])}."
    )


def _format_erc20_insufficient_balance(args: dict[str, Any]) -> str:
    return (
        f"Account {_format_value(args['sender'])} has insufficient PLACE balance: "
        f"balance {_format_place(args['balance'])}, required {_format_place(args['needed'])}."
    )


def _format_invalid_address(role: str, key: str) -> Any:
    def formatter(args: dict[str, Any]) -> str:
        return f"Invalid {role} address: {_format_value(args[key])}."

    return formatter


def _format_expired_signature(args: dict[str, Any]) -> str:
    return f"Permit signature expired at {_format_timestamp(args['deadline'])}."


def _format_invalid_signer(args: dict[str, Any]) -> str:
    return (
        "Permit signature was produced by "
        f"{_format_value(args['signer'])}, expected {_format_value(args['owner'])}."
    )


def _format_invalid_account_nonce(args: dict[str, Any]) -> str:
    return (
        f"Invalid nonce for {_format_value(args['account'])}. "
        f"Current nonce is {args['currentNonce']}."
    )


def _format_signature_length(args: dict[str, Any]) -> str:
    return f"Invalid ECDSA signature length: {args['length']} bytes."


def _format_signature_s(args: dict[str, Any]) -> str:
    return f"Invalid ECDSA signature `s` value: {_format_value(args['s'])}."


def _format_string_too_long(args: dict[str, Any]) -> str:
    return f"String is too long: {args['str']!r}."


_ERROR_FORMATTERS = {
    "ArrayLengthMismatch": _format_array_length_mismatch,
    "CellNotAvailable": _format_cell_not_available,
    "CooldownNotElapsed": _format_cooldown,
    "ECDSAInvalidSignature": lambda _args: "Invalid ECDSA signature.",
    "ECDSAInvalidSignatureLength": _format_signature_length,
    "ECDSAInvalidSignatureS": _format_signature_s,
    "ERC20InsufficientAllowance": _format_erc20_insufficient_allowance,
    "ERC20InsufficientBalance": _format_erc20_insufficient_balance,
    "ERC20InvalidApprover": _format_invalid_address("approver", "approver"),
    "ERC20InvalidReceiver": _format_invalid_address("receiver", "receiver"),
    "ERC20InvalidSender": _format_invalid_address("sender", "sender"),
    "ERC20InvalidSpender": _format_invalid_address("spender", "spender"),
    "ERC2612ExpiredSignature": _format_expired_signature,
    "ERC2612InvalidSigner": _format_invalid_signer,
    "InsufficientFaucetBalance": _format_insufficient_faucet_balance,
    "InvalidAccountNonce": _format_invalid_account_nonce,
    "InvalidRentDuration": _format_invalid_rent_duration,
    "InvalidRentPrice": _format_invalid_rent_price,
    "InvalidShortString": lambda _args: "Invalid short string encoding.",
    "NotCellRenter": _format_not_cell_renter,
    "OutOfBounds": _format_out_of_bounds,
    "OwnableInvalidOwner": _format_ownable_invalid_owner,
    "OwnableUnauthorizedAccount": _format_ownable_unauthorized,
    "SafeERC20FailedOperation": _format_safe_erc20_failed,
    "StringTooLong": _format_string_too_long,
    "TooManyCells": _format_too_many_cells,
}
