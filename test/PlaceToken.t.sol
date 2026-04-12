// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";

contract PlaceTokenTest is Test {
    PlaceToken public token;

    function setUp() public {
        token = new PlaceToken();
    }

    function test_Name() public view {
        assertEq(token.name(), "Place");
    }

    function test_Symbol() public view {
        assertEq(token.symbol(), "PLACE");
    }

    function test_Decimals() public view {
        assertEq(token.decimals(), 18);
    }

    function test_InitialSupply() public view {
        assertEq(token.totalSupply(), INITIAL_SUPPLY);
    }

    function test_InitialBalanceMintedToDeployer() public view {
        assertEq(token.balanceOf(address(this)), INITIAL_SUPPLY);
    }
}
