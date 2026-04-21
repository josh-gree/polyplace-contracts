// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {DeployScript} from "./Deploy.s.sol";
import {PlaceToken} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";
import {PlaceGrid} from "../src/PlaceGrid.sol";

contract SimulateScript is Script {
    // Anvil default accounts
    uint256 constant DEPLOYER_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    uint256 constant ALICE_KEY = 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d;
    uint256 constant BOB_KEY = 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a;

    function run() external {
        // --- Deploy ---
        // forge-lint: disable-next-line(unsafe-cheatcode)
        vm.setEnv("PRIVATE_KEY", vm.toString(DEPLOYER_KEY));
        DeployScript deployer = new DeployScript();
        (PlaceToken token, PlaceFaucet faucet, PlaceGrid grid) = deployer.run();

        console.log("Deployed token:  ", address(token));
        console.log("Deployed faucet: ", address(faucet));
        console.log("Deployed grid:   ", address(grid));

        // --- Alice: claim, approve, rent a red cell, then change it to green ---
        vm.startBroadcast(ALICE_KEY);
        faucet.claim();
        token.approve(address(grid), type(uint256).max);
        grid.rentCell(5, 10, 0xFF0000); // red
        grid.setColor(5, 10, 0x00FF00); // change to green
        vm.stopBroadcast();

        // --- Bob: claim, approve, rent a blue cell ---
        vm.startBroadcast(BOB_KEY);
        faucet.claim();
        token.approve(address(grid), type(uint256).max);
        grid.rentCell(20, 30, 0x0000FF); // blue
        vm.stopBroadcast();

        console.log("Simulation complete");
    }
}
