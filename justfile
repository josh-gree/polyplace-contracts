set dotenv-load

# List available recipes
default:
    @just --list

# Run all tests
test:
    forge test -v

# Start a local Anvil chain
anvil:
    anvil

# Deploy to local Anvil chain
deploy-local:
    forge script script/Deploy.s.sol --rpc-url localhost --broadcast
