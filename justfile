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
    forge test -v

# Start a local Anvil chain
anvil:
    anvil

# Deploy to local Anvil chain
deploy-local:
    forge script script/Deploy.s.sol --rpc-url localhost --broadcast

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
