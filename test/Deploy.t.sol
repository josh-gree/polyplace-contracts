// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";
import {DeployScript, DEPLOY_CLAIM_AMOUNT, DEPLOY_COOLDOWN} from "../script/Deploy.s.sol";

contract DeployTest is Test {
    PlaceToken public token;
    PlaceFaucet public faucet;

    address public deployer;

    uint256 constant TEST_PRIVATE_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;

    function setUp() public {
        vm.setEnv("PRIVATE_KEY", vm.toString(TEST_PRIVATE_KEY));
        deployer = vm.addr(TEST_PRIVATE_KEY);
        DeployScript script = new DeployScript();
        (token, faucet) = script.run();
    }

    function test_TokenSupply() public view {
        assertEq(token.totalSupply(), INITIAL_SUPPLY);
    }

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
}
