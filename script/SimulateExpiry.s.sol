// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {PlaceToken} from "../src/PlaceToken.sol";
import {PlaceGrid} from "../src/PlaceGrid.sol";

contract SimulateExpiryScript is Script {
    uint256 constant BOB_KEY = 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a;

    function run() external {
        PlaceToken token = PlaceToken(vm.envAddress("TOKEN_ADDRESS"));
        PlaceGrid grid   = PlaceGrid(vm.envAddress("GRID_ADDRESS"));

        console.log("Taking Alice's expired cell (5, 10) as Bob...");

        vm.startBroadcast(BOB_KEY);
        grid.rentCell(5, 10, 0xFFFF00); // yellow
        vm.stopBroadcast();

        uint32 cellId = uint32(10) * 1000 + 5;
        (address renter, uint24 color,) = grid.cells(cellId);
        console.log("Cell renter: ", renter);
        console.log("Cell color:  ", color);
    }
}
