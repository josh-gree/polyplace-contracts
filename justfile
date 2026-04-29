set dotenv-load

# List available recipes
default:
    @just --list

# Build the Python package (extracts ABIs and bytecode from Foundry artifacts)
build-package:
    forge build
    uv run --project packages/python python scripts/build_package.py

# Run all tests
test:
    FOUNDRY_OFFLINE=true forge test -v

# Start a local Anvil chain
anvil:
    anvil

# Deploy to local Anvil chain (anvil account 0); prints env block to stdout.
deploy-local:
    uv run --project packages/python polyplace-deploy \
        --rpc-url http://localhost:8545 \
        --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
        --env-out -

# Deploy to a named network (amoy, polygon); reads <NETWORK>_RPC_URL and <NETWORK>_PRIVATE_KEY from .env.
deploy network:
    #!/usr/bin/env bash
    set -euo pipefail
    NETWORK_UPPER="$(echo {{network}} | tr '[:lower:]' '[:upper:]')"
    RPC_VAR="${NETWORK_UPPER}_RPC_URL"
    KEY_VAR="${NETWORK_UPPER}_PRIVATE_KEY"
    : "${!RPC_VAR:?set $RPC_VAR in .env}"
    : "${!KEY_VAR:?set $KEY_VAR in .env}"
    uv run --project packages/python polyplace-deploy \
        --rpc-url "${!RPC_VAR}" \
        --private-key "${!KEY_VAR}" \
        --manifest-out ".forge-manifests/{{network}}.json"

# Run the polyplace-dev CLI against any deployed manifest.
# Usage: just dev <manifest-path> <wallet-name> <cli-args...>
#   e.g. just dev .forge-manifests/amoy.json polyplace-amoy-deploy faucet claim
# RPC URL is resolved from the manifest's chainId.
dev manifest wallet *args:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${WALLET_MASTER_PASSWORD:?set WALLET_MASTER_PASSWORD in .env}"
    MANIFEST="{{manifest}}"
    [[ -f "$MANIFEST" ]] || { echo "Error: $MANIFEST not found" >&2; exit 1; }
    CHAIN_ID="$(jq -r .chainId "$MANIFEST")"
    case "$CHAIN_ID" in
        80002)  RPC_URL="${AMOY_RPC_URL:?set AMOY_RPC_URL in .env}" ;;
        137)    RPC_URL="${POLYGON_RPC_URL:?set POLYGON_RPC_URL in .env}" ;;
        31337)  RPC_URL="http://localhost:8545" ;;
        *)      echo "Error: no RPC URL mapping for chainId $CHAIN_ID — add one to the dev recipe" >&2; exit 1 ;;
    esac
    WALLET_GEN="${WALLET_GEN_PATH:-$HOME/src/wallet-gen}"
    export WALLET_NAME={{wallet}}
    export POLYPLACE_RPC_URL="$RPC_URL"
    export POLYPLACE_TOKEN_ADDRESS="$(jq -r .token "$MANIFEST")"
    export POLYPLACE_FAUCET_ADDRESS="$(jq -r .faucet "$MANIFEST")"
    export POLYPLACE_GRID_ADDRESS="$(jq -r .grid "$MANIFEST")"
    export POLYPLACE_PRIVATE_KEY="$(uv run --project "$WALLET_GEN" python -c 'import os; from wallet_gen import api; print(api.get_private_key(os.environ["WALLET_NAME"]))')"
    uv run --project packages/python polyplace-dev {{args}}

