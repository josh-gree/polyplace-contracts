// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script} from "forge-std/Script.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";
import {PlaceGrid} from "../src/PlaceGrid.sol";

uint256 constant DEPLOY_CLAIM_AMOUNT  = 100 * 10 ** 18;
uint256 constant DEPLOY_COOLDOWN      = 1 days;
uint256 constant DEPLOY_RENT_PRICE    = 10 * 10 ** 18;
uint256 constant DEPLOY_RENT_DURATION = 1 days;

contract DeployScript is Script {
    using SafeERC20 for IERC20;

    function run() external returns (PlaceToken token, PlaceFaucet faucet, PlaceGrid grid) {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        vm.startBroadcast(deployerKey);

        token  = new PlaceToken();
        faucet = new PlaceFaucet(address(token), DEPLOY_CLAIM_AMOUNT, DEPLOY_COOLDOWN, deployer);
        grid   = new PlaceGrid(address(token), address(faucet), DEPLOY_RENT_PRICE, DEPLOY_RENT_DURATION, deployer);
        IERC20(address(token)).safeTransfer(address(faucet), INITIAL_SUPPLY);

        vm.stopBroadcast();
    }
}
