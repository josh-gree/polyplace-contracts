// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script} from "forge-std/Script.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";

uint256 constant DEPLOY_CLAIM_AMOUNT = 100 * 10 ** 18;
uint256 constant DEPLOY_COOLDOWN = 1 days;

contract DeployScript is Script {

    function run() external returns (PlaceToken token, PlaceFaucet faucet) {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        vm.startBroadcast(deployerKey);

        token = new PlaceToken();
        faucet = new PlaceFaucet(address(token), DEPLOY_CLAIM_AMOUNT, DEPLOY_COOLDOWN, deployer);
        token.transfer(address(faucet), INITIAL_SUPPLY);

        vm.stopBroadcast();
    }
}
