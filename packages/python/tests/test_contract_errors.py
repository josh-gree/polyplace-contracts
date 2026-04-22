from __future__ import annotations

import unittest

from eth_utils import keccak
from web3 import Web3
from web3.exceptions import ContractCustomError

from polyplace_contracts import PolyplaceContractError
from polyplace_contracts.cli.wrappers import _ContractWrapper
from polyplace_contracts.errors import decode_contract_error_data, translate_contract_error


def _encode_error(signature: str, arg_types: list[str], values: list[object]) -> str:
    selector = keccak(text=signature)[:4].hex()
    payload = Web3().codec.encode(arg_types, values).hex() if arg_types else ""
    return f"0x{selector}{payload}"


class _RaisingFunctions:
    def __init__(self, error_data: str) -> None:
        self._error_data = error_data

    def __getitem__(self, _name: str) -> "_RaisingFunctions":
        return self

    def __call__(self, *_args: object) -> "_RaisingFunctions":
        return self

    def call(self) -> object:
        raise ContractCustomError(self._error_data, data=self._error_data)


class _DummyContract:
    def __init__(self, error_data: str) -> None:
        self.functions = _RaisingFunctions(error_data)


class ContractErrorTests(unittest.TestCase):
    def test_decode_out_of_bounds_data(self) -> None:
        data = _encode_error("OutOfBounds(uint16,uint16)", ["uint16", "uint16"], [1000, 1000])

        decoded = decode_contract_error_data(data)

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.name, "OutOfBounds")
        self.assertEqual(dict(decoded.arguments), {"x": 1000, "y": 1000})

    def test_translate_known_custom_error(self) -> None:
        data = _encode_error("OutOfBounds(uint16,uint16)", ["uint16", "uint16"], [1000, 1000])
        exc = ContractCustomError(data, data=data)

        translated = translate_contract_error(exc)

        self.assertIsInstance(translated, PolyplaceContractError)
        self.assertEqual(
            str(translated),
            "Cell coordinates out of bounds: x=1000, y=1000. Valid range is 0-999.",
        )
        self.assertEqual(translated.error_name, "OutOfBounds")

    def test_translate_unknown_custom_error(self) -> None:
        data = "0xdeadbeef"
        exc = ContractCustomError(data, data=data)

        translated = translate_contract_error(exc)

        self.assertEqual(
            str(translated),
            "Contract reverted with an unknown custom error (selector 0xdeadbeef).",
        )
        self.assertIsNone(translated.error_name)

    def test_wrapper_rewrites_web3_error(self) -> None:
        data = _encode_error("CooldownNotElapsed(uint256)", ["uint256"], [1_700_000_000])
        wrapper = object.__new__(_ContractWrapper)
        wrapper._contract = _DummyContract(data)

        with self.assertRaises(PolyplaceContractError) as raised:
            wrapper._call("claim")

        self.assertIn("Faucet cooldown has not elapsed.", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
