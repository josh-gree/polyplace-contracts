"""
Extract ABI and bytecode from Foundry artifacts into the Python package.
Run via: just build-package
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
OUT_DIR   = REPO_ROOT / "out"
DEST_DIR  = REPO_ROOT / "packages" / "python" / "polyplace_contracts" / "artifacts"

CONTRACTS = ["PlaceToken", "PlaceFaucet", "PlaceGrid"]

def extract(contract: str) -> None:
    src = OUT_DIR / f"{contract}.sol" / f"{contract}.json"
    if not src.exists():
        raise FileNotFoundError(f"Artifact not found: {src}. Run 'forge build' first.")

    with open(src) as f:
        artifact = json.load(f)

    extracted = {
        "abi":      artifact["abi"],
        "bytecode": artifact["bytecode"]["object"],
    }

    dest = DEST_DIR / f"{contract}.json"
    with open(dest, "w") as f:
        json.dump(extracted, f, indent=2)

    print(f"  {contract} -> {dest.relative_to(REPO_ROOT)}")

if __name__ == "__main__":
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    print("Extracting artifacts...")
    for contract in CONTRACTS:
        extract(contract)
    print("Done.")
