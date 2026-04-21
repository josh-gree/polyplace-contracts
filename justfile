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

# Deploy to local Anvil chain
deploy-local:
    forge script script/Deploy.s.sol --rpc-url localhost --broadcast

# Deploy to a named network (amoy, polygon) with source verification.
# Resolves PRIVATE_KEY from wallet-gen using <NETWORK>_DEPLOY_WALLET_NAME and
# WALLET_MASTER_PASSWORD from .env. Writes the manifest to
# .forge-manifests/<network>.json.
deploy network:
    #!/usr/bin/env bash
    set -euo pipefail
    PRIVATE_KEY="$(just _resolve-private-key {{network}})"
    export PRIVATE_KEY
    export POLYPLACE_DEPLOYMENT_MANIFEST_PATH=".forge-manifests/{{network}}.json"
    FOUNDRY_OFFLINE=false forge script script/Deploy.s.sol --rpc-url {{network}} --broadcast --verify

# Simulate a deploy against a named network (no broadcast, no verify).
deploy-dry network:
    #!/usr/bin/env bash
    set -euo pipefail
    PRIVATE_KEY="$(just _resolve-private-key {{network}})"
    export PRIVATE_KEY
    FOUNDRY_OFFLINE=false forge script script/Deploy.s.sol --rpc-url {{network}}

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

_resolve-private-key network:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${WALLET_MASTER_PASSWORD:?set WALLET_MASTER_PASSWORD in .env}"
    NETWORK_UPPER="$(echo {{network}} | tr '[:lower:]' '[:upper:]')"
    WALLET_VAR="${NETWORK_UPPER}_DEPLOY_WALLET_NAME"
    WALLET_NAME="${!WALLET_VAR:-}"
    if [[ -z "$WALLET_NAME" ]]; then
        echo "Error: $WALLET_VAR is not set in .env" >&2
        exit 1
    fi
    WALLET_GEN="${WALLET_GEN_PATH:-$HOME/src/wallet-gen}"
    export WALLET_NAME
    uv run --project "$WALLET_GEN" python -c 'import os; from wallet_gen import api; print(api.get_private_key(os.environ["WALLET_NAME"]))'

# Simulate usage against local Anvil chain (shows emitted events with -vvvv)
# Requires: jq
simulate:
    #!/usr/bin/env bash
    set -e
    forge script script/Simulate.s.sol --rpc-url localhost --broadcast -vvvv
    TOKEN_ADDRESS=$(jq -r '[.transactions[] | select(.contractName == "PlaceToken")] | last | .contractAddress' broadcast/Simulate.s.sol/31337/run-latest.json)
    GRID_ADDRESS=$(jq -r '[.transactions[] | select(.contractName == "PlaceGrid")] | last | .contractAddress' broadcast/Simulate.s.sol/31337/run-latest.json)
    echo "Advancing time by 2 days..."
    cast rpc --rpc-url localhost anvil_increaseTime 172800
    cast rpc --rpc-url localhost anvil_mine 1
    TOKEN_ADDRESS=$TOKEN_ADDRESS GRID_ADDRESS=$GRID_ADDRESS \
        forge script script/SimulateExpiry.s.sol --rpc-url localhost --broadcast -vvvv
