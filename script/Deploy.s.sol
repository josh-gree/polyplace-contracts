// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script} from "forge-std/Script.sol";
import {stdJson} from "forge-std/StdJson.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";
import {PlaceGrid} from "../src/PlaceGrid.sol";

uint256 constant DEPLOY_CLAIM_AMOUNT = 100 * 10 ** 18;
uint256 constant DEPLOY_COOLDOWN = 1 days;
uint256 constant DEPLOY_RENT_PRICE = 10 * 10 ** 18;
uint256 constant DEPLOY_RENT_DURATION = 1 days;

contract DeployScript is Script {
    using SafeERC20 for IERC20;
    using stdJson for string;

    function run() external returns (PlaceToken token, PlaceFaucet faucet, PlaceGrid grid) {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);
        uint256 claimAmount = vm.envOr("POLYPLACE_DEPLOY_CLAIM_AMOUNT", DEPLOY_CLAIM_AMOUNT);
        uint256 cooldown = vm.envOr("POLYPLACE_DEPLOY_COOLDOWN", DEPLOY_COOLDOWN);
        uint256 rentPrice = vm.envOr("POLYPLACE_DEPLOY_RENT_PRICE", DEPLOY_RENT_PRICE);
        uint256 rentDuration = vm.envOr("POLYPLACE_DEPLOY_RENT_DURATION", DEPLOY_RENT_DURATION);

        vm.startBroadcast(deployerKey);

        token = new PlaceToken();
        faucet = new PlaceFaucet(address(token), claimAmount, cooldown, deployer);
        grid = new PlaceGrid(address(token), address(faucet), rentPrice, rentDuration, deployer);
        IERC20(address(token)).safeTransfer(address(faucet), INITIAL_SUPPLY);

        vm.stopBroadcast();

        _writeManifest(token, faucet, grid, deployer, claimAmount, cooldown, rentPrice, rentDuration);
    }

    function _writeManifest(
        PlaceToken token,
        PlaceFaucet faucet,
        PlaceGrid grid,
        address deployer,
        uint256 claimAmount,
        uint256 cooldown,
        uint256 rentPrice,
        uint256 rentDuration
    ) internal {
        string memory manifestPath = vm.envOr("POLYPLACE_DEPLOYMENT_MANIFEST_PATH", string(""));
        if (bytes(manifestPath).length == 0) {
            return;
        }

        string memory jsonKey = "deployment";
        string memory json = vm.serializeAddress(jsonKey, "token", address(token));
        json = vm.serializeAddress(jsonKey, "faucet", address(faucet));
        json = vm.serializeAddress(jsonKey, "grid", address(grid));
        json = vm.serializeUint(jsonKey, "chainId", block.chainid);
        json = vm.serializeAddress(jsonKey, "deployer", deployer);
        json = vm.serializeString(jsonKey, "initialSupply", vm.toString(INITIAL_SUPPLY));
        json = vm.serializeString(jsonKey, "claimAmount", vm.toString(claimAmount));
        json = vm.serializeUint(jsonKey, "cooldown", cooldown);
        json = vm.serializeString(jsonKey, "rentPrice", vm.toString(rentPrice));
        json = vm.serializeUint(jsonKey, "rentDuration", rentDuration);
        json.write(manifestPath);
    }
}
