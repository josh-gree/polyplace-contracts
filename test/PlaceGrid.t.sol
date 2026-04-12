// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {PlaceToken, INITIAL_SUPPLY} from "../src/PlaceToken.sol";
import {PlaceFaucet} from "../src/PlaceFaucet.sol";
import {PlaceGrid} from "../src/PlaceGrid.sol";

contract PlaceGridTest is Test {
    using SafeERC20 for IERC20;

    PlaceToken public token;
    PlaceFaucet public faucet;
    PlaceGrid public grid;

    address public owner = makeAddr("owner");
    address public alice = makeAddr("alice");
    address public bob   = makeAddr("bob");

    uint256 constant PERMIT_PRIVATE_KEY = 0x12345;
    address public permitUser = vm.addr(PERMIT_PRIVATE_KEY);

    uint256 constant CLAIM_AMOUNT  = 100 * 10 ** 18;
    uint256 constant RENT_PRICE    = 10 * 10 ** 18;
    uint256 constant RENT_DURATION = 1 days;

    function setUp() public {
        token  = new PlaceToken();
        faucet = new PlaceFaucet(address(token), CLAIM_AMOUNT, 1 days, owner);
        grid   = new PlaceGrid(address(token), address(faucet), RENT_PRICE, RENT_DURATION, owner);

        IERC20(address(token)).safeTransfer(address(faucet), INITIAL_SUPPLY);

        _giveTokensAndApprove(alice, RENT_PRICE * 10);
        _giveTokensAndApprove(bob,   RENT_PRICE * 10);
        deal(address(token), permitUser, RENT_PRICE * 10);
    }

    function _giveTokensAndApprove(address user, uint256 amount) internal {
        deal(address(token), user, amount);
        vm.prank(user);
        token.approve(address(grid), type(uint256).max);
    }

    // --- constructor ---

    function test_Token() public view {
        assertEq(address(grid.TOKEN()), address(token));
    }

    function test_Faucet() public view {
        assertEq(grid.FAUCET(), address(faucet));
    }

    function test_RentPrice() public view {
        assertEq(grid.rentPrice(), RENT_PRICE);
    }

    function test_RentDuration() public view {
        assertEq(grid.rentDuration(), RENT_DURATION);
    }

    function test_Owner() public view {
        assertEq(grid.owner(), owner);
    }

    function test_GridSize() public view {
        assertEq(grid.GRID_SIZE(), 1000);
    }

    // --- rentCell ---

    function test_RentCell() public {
        uint32 cellId = uint32(10) * 1000 + 5; // y=10, x=5

        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        (address renter, uint24 color, uint64 expiresAt) = grid.cells(cellId);
        assertEq(renter, alice);
        assertEq(color, 0xFF0000);
        assertEq(expiresAt, block.timestamp + RENT_DURATION);
    }

    function test_RentCellDeductsTokensFromRenter() public {
        uint256 balanceBefore = token.balanceOf(alice);

        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        assertEq(token.balanceOf(alice), balanceBefore - RENT_PRICE);
    }

    function test_RentCellSendsTokensToFaucet() public {
        uint256 balanceBefore = token.balanceOf(address(faucet));

        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        assertEq(token.balanceOf(address(faucet)), balanceBefore + RENT_PRICE);
    }

    function test_RentCellEmitsCellRentedEvent() public {
        uint32 cellId = uint32(10) * 1000 + 5;
        uint256 expectedExpiry = block.timestamp + RENT_DURATION;

        vm.expectEmit(true, true, false, true);
        emit PlaceGrid.CellRented(cellId, alice, expectedExpiry);

        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);
    }

    function test_RentCellEmitsCellColorUpdatedEvent() public {
        uint32 cellId = uint32(10) * 1000 + 5;

        vm.expectEmit(true, true, false, true);
        emit PlaceGrid.CellColorUpdated(cellId, alice, 0xFF0000);

        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);
    }

    function test_RentCellAtCorners() public {
        vm.startPrank(alice);
        grid.rentCell(0,   0,   0x000001);
        grid.rentCell(999, 0,   0x000002);
        grid.rentCell(0,   999, 0x000003);
        grid.rentCell(999, 999, 0x000004);
        vm.stopPrank();

        (address r1,,) = grid.cells(0);
        (address r2,,) = grid.cells(999);
        (address r3,,) = grid.cells(999 * 1000);
        (address r4,,) = grid.cells(999 * 1000 + 999);

        assertEq(r1, alice);
        assertEq(r2, alice);
        assertEq(r3, alice);
        assertEq(r4, alice);
    }

    function test_RentCellRevertsIfOutOfBoundsX() public {
        vm.expectRevert(abi.encodeWithSelector(PlaceGrid.OutOfBounds.selector, 1000, 0));
        vm.prank(alice);
        grid.rentCell(1000, 0, 0xFF0000);
    }

    function test_RentCellRevertsIfOutOfBoundsY() public {
        vm.expectRevert(abi.encodeWithSelector(PlaceGrid.OutOfBounds.selector, 0, 1000));
        vm.prank(alice);
        grid.rentCell(0, 1000, 0xFF0000);
    }

    function test_RentCellRevertsIfCellActiveAndDifferentRenter() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        uint32 cellId = uint32(10) * 1000 + 5;
        // forge-lint: disable-next-line(unsafe-typecast)
        uint64 expiresAt = uint64(block.timestamp + RENT_DURATION);

        vm.expectRevert(abi.encodeWithSelector(PlaceGrid.CellNotAvailable.selector, cellId, expiresAt));
        vm.prank(bob);
        grid.rentCell(5, 10, 0x0000FF);
    }

    function test_RentCellAllowsRenterToRenewBeforeExpiry() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        vm.warp(block.timestamp + RENT_DURATION / 2);

        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        uint32 cellId = uint32(10) * 1000 + 5;
        (,, uint64 expiresAt) = grid.cells(cellId);
        assertEq(expiresAt, block.timestamp + RENT_DURATION);
    }

    function test_RentCellAllowsRenterToChangeColorOnRenewal() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        vm.prank(alice);
        grid.rentCell(5, 10, 0x0000FF);

        uint32 cellId = uint32(10) * 1000 + 5;
        (, uint24 color,) = grid.cells(cellId);
        assertEq(color, 0x0000FF);
    }

    function test_RentCellSucceedsAfterExpiry() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        vm.warp(block.timestamp + RENT_DURATION + 1);

        vm.prank(bob);
        grid.rentCell(5, 10, 0x0000FF);

        uint32 cellId = uint32(10) * 1000 + 5;
        (address renter,,) = grid.cells(cellId);
        assertEq(renter, bob);
    }

    function test_RentCellRevertsIfInsufficientAllowance() public {
        vm.prank(alice);
        token.approve(address(grid), 0);

        vm.expectRevert();
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);
    }

    function test_RentCellWithPermit() public {
        uint256 deadline = block.timestamp + 1 hours;
        (uint8 v, bytes32 r, bytes32 s) = _signPermit(PERMIT_PRIVATE_KEY, address(grid), RENT_PRICE, deadline);

        vm.prank(permitUser);
        grid.rentCell(5, 10, 0xFF0000, deadline, v, r, s);

        uint32 cellId = uint32(10) * 1000 + 5;
        (address renter,,) = grid.cells(cellId);
        assertEq(renter, permitUser);
        assertEq(token.balanceOf(permitUser), RENT_PRICE * 10 - RENT_PRICE);
    }

    function test_RentCellWithPermitRevertsIfExpired() public {
        uint256 deadline = block.timestamp + 1 hours;
        (uint8 v, bytes32 r, bytes32 s) = _signPermit(PERMIT_PRIVATE_KEY, address(grid), RENT_PRICE, deadline);

        vm.warp(deadline + 1);

        vm.expectRevert();
        vm.prank(permitUser);
        grid.rentCell(5, 10, 0xFF0000, deadline, v, r, s);
    }

    function _signPermit(
        uint256 privateKey,
        address spender,
        uint256 value,
        uint256 deadline
    ) internal view returns (uint8 v, bytes32 r, bytes32 s) {
        address user = vm.addr(privateKey);
        bytes32 domainSeparator = token.DOMAIN_SEPARATOR();
        bytes32 permitHash = keccak256(abi.encode(
            keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
            user,
            spender,
            value,
            token.nonces(user),
            deadline
        ));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domainSeparator, permitHash));
        (v, r, s) = vm.sign(privateKey, digest);
    }

    function test_RentCellRevertsIfInsufficientBalance() public {
        address broke = makeAddr("broke");
        vm.prank(broke);
        token.approve(address(grid), type(uint256).max);

        vm.expectRevert();
        vm.prank(broke);
        grid.rentCell(5, 10, 0xFF0000);
    }

    // --- setColor ---

    function test_SetColor() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        vm.prank(alice);
        grid.setColor(5, 10, 0x00FF00);

        uint32 cellId = uint32(10) * 1000 + 5;
        (, uint24 color,) = grid.cells(cellId);
        assertEq(color, 0x00FF00);
    }

    function test_SetColorDoesNotChargeTokens() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        uint256 balanceAfterRent = token.balanceOf(alice);

        vm.prank(alice);
        grid.setColor(5, 10, 0x00FF00);

        assertEq(token.balanceOf(alice), balanceAfterRent);
    }

    function test_SetColorEmitsEvent() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        uint32 cellId = uint32(10) * 1000 + 5;

        vm.expectEmit(true, true, false, true);
        emit PlaceGrid.CellColorUpdated(cellId, alice, 0x00FF00);

        vm.prank(alice);
        grid.setColor(5, 10, 0x00FF00);
    }

    function test_SetColorRevertsIfNotRenter() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        uint32 cellId = uint32(10) * 1000 + 5;

        vm.expectRevert(abi.encodeWithSelector(PlaceGrid.NotCellRenter.selector, cellId));
        vm.prank(bob);
        grid.setColor(5, 10, 0x0000FF);
    }

    function test_SetColorRevertsIfRentalExpired() public {
        vm.prank(alice);
        grid.rentCell(5, 10, 0xFF0000);

        vm.warp(block.timestamp + RENT_DURATION + 1);

        uint32 cellId = uint32(10) * 1000 + 5;

        vm.expectRevert(abi.encodeWithSelector(PlaceGrid.NotCellRenter.selector, cellId));
        vm.prank(alice);
        grid.setColor(5, 10, 0x00FF00);
    }

    function test_SetColorRevertsIfOutOfBounds() public {
        vm.expectRevert(abi.encodeWithSelector(PlaceGrid.OutOfBounds.selector, 1000, 0));
        vm.prank(alice);
        grid.setColor(1000, 0, 0xFF0000);
    }

    // --- setRentPrice ---

    function test_SetRentPrice() public {
        uint256 newPrice = 20 * 10 ** 18;
        vm.prank(owner);
        grid.setRentPrice(newPrice);
        assertEq(grid.rentPrice(), newPrice);
    }

    function test_SetRentPriceEmitsEvent() public {
        uint256 newPrice = 20 * 10 ** 18;

        vm.expectEmit(false, false, false, true);
        emit PlaceGrid.RentPriceUpdated(RENT_PRICE, newPrice);

        vm.prank(owner);
        grid.setRentPrice(newPrice);
    }

    function test_SetRentPriceRevertsIfZero() public {
        vm.expectRevert(PlaceGrid.InvalidRentPrice.selector);
        vm.prank(owner);
        grid.setRentPrice(0);
    }

    function test_SetRentPriceRevertsIfNotOwner() public {
        vm.expectRevert();
        vm.prank(alice);
        grid.setRentPrice(20 * 10 ** 18);
    }

    // --- setRentDuration ---

    function test_SetRentDuration() public {
        uint256 newDuration = 2 days;
        vm.prank(owner);
        grid.setRentDuration(newDuration);
        assertEq(grid.rentDuration(), newDuration);
    }

    function test_SetRentDurationEmitsEvent() public {
        uint256 newDuration = 2 days;

        vm.expectEmit(false, false, false, true);
        emit PlaceGrid.RentDurationUpdated(RENT_DURATION, newDuration);

        vm.prank(owner);
        grid.setRentDuration(newDuration);
    }

    function test_SetRentDurationRevertsIfZero() public {
        vm.expectRevert(PlaceGrid.InvalidRentDuration.selector);
        vm.prank(owner);
        grid.setRentDuration(0);
    }

    function test_SetRentDurationRevertsIfNotOwner() public {
        vm.expectRevert();
        vm.prank(alice);
        grid.setRentDuration(2 days);
    }
}
