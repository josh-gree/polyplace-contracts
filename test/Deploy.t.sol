// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";
import {PlaceGrid} from "../src/PlaceGrid.sol";
import {
    DeployScript,
    DEPLOY_CLAIM_AMOUNT,
    DEPLOY_COOLDOWN,
    DEPLOY_RENT_PRICE,
    DEPLOY_RENT_DURATION
} from "../script/Deploy.s.sol";

contract DeployTest is Test {
    PlaceToken public token;
    PlaceFaucet public faucet;
    PlaceGrid public grid;

    address public deployer;

    uint256 constant TEST_PRIVATE_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;

    function setUp() public {
        // forge-lint: disable-next-line(unsafe-cheatcode)
        vm.setEnv("PRIVATE_KEY", vm.toString(TEST_PRIVATE_KEY));
        // Pin deploy overrides so a developer's .env (loaded by `just test`)
        // can't leak public-network values into the in-process script run.
        // forge-lint: disable-next-line(unsafe-cheatcode)
        vm.setEnv("POLYPLACE_DEPLOY_CLAIM_AMOUNT", vm.toString(DEPLOY_CLAIM_AMOUNT));
        // forge-lint: disable-next-line(unsafe-cheatcode)
        vm.setEnv("POLYPLACE_DEPLOY_COOLDOWN", vm.toString(DEPLOY_COOLDOWN));
        // forge-lint: disable-next-line(unsafe-cheatcode)
        vm.setEnv("POLYPLACE_DEPLOY_RENT_PRICE", vm.toString(DEPLOY_RENT_PRICE));
        // forge-lint: disable-next-line(unsafe-cheatcode)
        vm.setEnv("POLYPLACE_DEPLOY_RENT_DURATION", vm.toString(DEPLOY_RENT_DURATION));
        // Empty path keeps the script on its early-return branch and prevents
        // overwriting .forge-manifests/<network>.json during tests.
        // forge-lint: disable-next-line(unsafe-cheatcode)
        vm.setEnv("POLYPLACE_DEPLOYMENT_MANIFEST_PATH", "");
        deployer = vm.addr(TEST_PRIVATE_KEY);
        DeployScript script = new DeployScript();
        (token, faucet, grid) = script.run();
    }

    // --- token ---

    function test_TokenSupply() public view {
        assertEq(token.totalSupply(), INITIAL_SUPPLY);
    }

    // --- faucet ---

    function test_FaucetHoldsEntireSupply() public view {
        assertEq(token.balanceOf(address(faucet)), INITIAL_SUPPLY);
    }

    function test_DeployerBalanceIsZero() public view {
        assertEq(token.balanceOf(deployer), 0);
    }

    function test_FaucetToken() public view {
        assertEq(address(faucet.TOKEN()), address(token));
    }

    function test_FaucetOwnerIsDeployer() public view {
        assertEq(faucet.owner(), deployer);
    }

    function test_FaucetClaimAmount() public view {
        assertEq(faucet.claimAmount(), DEPLOY_CLAIM_AMOUNT);
    }

    function test_FaucetCooldown() public view {
        assertEq(faucet.cooldown(), DEPLOY_COOLDOWN);
    }

    // --- grid ---

    function test_GridToken() public view {
        assertEq(address(grid.TOKEN()), address(token));
    }

    function test_GridFaucet() public view {
        assertEq(grid.FAUCET(), address(faucet));
    }

    function test_GridOwnerIsDeployer() public view {
        assertEq(grid.owner(), deployer);
    }

    function test_GridRentPrice() public view {
        assertEq(grid.rentPrice(), DEPLOY_RENT_PRICE);
    }

    function test_GridRentDuration() public view {
        assertEq(grid.rentDuration(), DEPLOY_RENT_DURATION);
    }
}
