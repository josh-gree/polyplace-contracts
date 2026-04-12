// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";

contract PlaceFaucetTest is Test {
    using SafeERC20 for IERC20;
    PlaceToken public token;
    PlaceFaucet public faucet;

    address public owner = makeAddr("owner");
    address public user = makeAddr("user");

    uint256 constant CLAIM_AMOUNT = 100 * 10 ** 18;
    uint256 constant COOLDOWN = 1 days;

    function setUp() public {
        token = new PlaceToken();
        faucet = new PlaceFaucet(address(token), CLAIM_AMOUNT, COOLDOWN, owner);
        IERC20(address(token)).safeTransfer(address(faucet), INITIAL_SUPPLY);
    }

    // --- constructor ---

    function test_Token() public view {
        assertEq(address(faucet.TOKEN()), address(token));
    }

    function test_ClaimAmount() public view {
        assertEq(faucet.claimAmount(), CLAIM_AMOUNT);
    }

    function test_Cooldown() public view {
        assertEq(faucet.cooldown(), COOLDOWN);
    }

    function test_Owner() public view {
        assertEq(faucet.owner(), owner);
    }

    // --- claim ---

    function test_Claim() public {
        vm.prank(user);
        faucet.claim();

        assertEq(token.balanceOf(user), CLAIM_AMOUNT);
        assertEq(token.balanceOf(address(faucet)), INITIAL_SUPPLY - CLAIM_AMOUNT);
    }

    function test_ClaimUpdatesLastClaimed() public {
        vm.prank(user);
        faucet.claim();

        assertEq(faucet.lastClaimed(user), block.timestamp);
    }

    function test_ClaimEmitsEvent() public {
        vm.expectEmit(true, false, false, true);
        emit PlaceFaucet.Claimed(user, CLAIM_AMOUNT);

        vm.prank(user);
        faucet.claim();
    }

    function test_ClaimAfterCooldown() public {
        vm.prank(user);
        faucet.claim();

        vm.warp(block.timestamp + COOLDOWN);

        vm.prank(user);
        faucet.claim();

        assertEq(token.balanceOf(user), CLAIM_AMOUNT * 2);
    }

    function test_ClaimRevertsIfCooldownNotElapsed() public {
        vm.prank(user);
        faucet.claim();

        uint256 availableAt = faucet.lastClaimed(user) + COOLDOWN;

        vm.expectRevert(abi.encodeWithSelector(PlaceFaucet.CooldownNotElapsed.selector, availableAt));
        vm.prank(user);
        faucet.claim();
    }

    function test_ClaimRevertsIfFaucetEmpty() public {
        // Deploy a fresh faucet with no tokens
        PlaceFaucet emptyFaucet = new PlaceFaucet(address(token), CLAIM_AMOUNT, COOLDOWN, owner);

        vm.expectRevert(abi.encodeWithSelector(PlaceFaucet.InsufficientFaucetBalance.selector, 0, CLAIM_AMOUNT));
        vm.prank(user);
        emptyFaucet.claim();
    }

    // --- setClaimAmount ---

    function test_SetClaimAmount() public {
        uint256 newAmount = 200 * 10 ** 18;

        vm.prank(owner);
        faucet.setClaimAmount(newAmount);

        assertEq(faucet.claimAmount(), newAmount);
    }

    function test_SetClaimAmountEmitsEvent() public {
        uint256 newAmount = 200 * 10 ** 18;

        vm.expectEmit(false, false, false, true);
        emit PlaceFaucet.ClaimAmountUpdated(CLAIM_AMOUNT, newAmount);

        vm.prank(owner);
        faucet.setClaimAmount(newAmount);
    }

    function test_SetClaimAmountRevertsIfNotOwner() public {
        vm.expectRevert();
        vm.prank(user);
        faucet.setClaimAmount(200 * 10 ** 18);
    }

    // --- setCooldown ---

    function test_SetCooldown() public {
        uint256 newCooldown = 2 days;

        vm.prank(owner);
        faucet.setCooldown(newCooldown);

        assertEq(faucet.cooldown(), newCooldown);
    }

    function test_SetCooldownEmitsEvent() public {
        uint256 newCooldown = 2 days;

        vm.expectEmit(false, false, false, true);
        emit PlaceFaucet.CooldownUpdated(COOLDOWN, newCooldown);

        vm.prank(owner);
        faucet.setCooldown(newCooldown);
    }

    function test_SetCooldownRevertsIfNotOwner() public {
        vm.expectRevert();
        vm.prank(user);
        faucet.setCooldown(2 days);
    }
}
