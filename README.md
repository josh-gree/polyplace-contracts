# polyplace-contracts

Smart contracts for Polyplace — a grid-based game on Polygon PoS.

## Contracts

### PlaceToken
ERC20 token (symbol: PLACE) with a fixed supply of 1,000,000,000 tokens minted to the deployer. No minting after deploy.

### PlaceFaucet
Distributes PLACE tokens to players. Each address can claim a configurable amount once per cooldown period. Tokens spent in the game flow back to the faucet, keeping supply in circulation.

### PlaceGrid
A 1000×1000 grid where players spend PLACE to rent individual cells. Each cell has an owner and a colour (packed RGB `uint24`). Rentals expire after a configurable duration, at which point the cell becomes available again.

## Development

### Prerequisites
- [Foundry](https://getfoundry.sh/)
- [just](https://just.systems/)

### Setup
```shell
cp .env.example .env
```

### Commands
```shell
just test          # run all tests
just anvil         # start a local chain
just deploy-local  # deploy to local Anvil chain
```

