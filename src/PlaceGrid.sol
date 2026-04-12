// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Permit.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract PlaceGrid is Ownable {
    using SafeERC20 for IERC20;

    uint16 public constant GRID_SIZE = 1000;

    IERC20  public immutable TOKEN;
    address public immutable FAUCET;

    struct Cell {
        address renter;    // 20 bytes
        uint24  color;     //  3 bytes  ─┐ packed into one
        uint64  expiresAt; //  8 bytes  ─┘ 32-byte slot
    }

    mapping(uint32 cellId => Cell) public cells;

    uint256 public rentPrice;
    uint256 public rentDuration;

    error OutOfBounds(uint16 x, uint16 y);
    error CellNotAvailable(uint32 cellId, uint256 expiresAt);
    error NotCellRenter(uint32 cellId);
    error InvalidRentPrice();
    error InvalidRentDuration();

    event CellRented(uint32 indexed cellId, address indexed renter, uint256 expiresAt);
    event CellColorUpdated(uint32 indexed cellId, address indexed renter, uint24 color);
    event RentPriceUpdated(uint256 oldPrice, uint256 newPrice);
    event RentDurationUpdated(uint256 oldDuration, uint256 newDuration);

    constructor(
        address token_,
        address faucet_,
        uint256 rentPrice_,
        uint256 rentDuration_,
        address owner_
    ) Ownable(owner_) {
        TOKEN        = IERC20(token_);
        FAUCET       = faucet_;
        rentPrice    = rentPrice_;
        rentDuration = rentDuration_;
    }

    /// @notice Spend PLACE tokens to rent a cell and set its colour.
    /// @param x     Column, 0–999.
    /// @param y     Row, 0–999.
    /// @param color Packed RGB: (r << 16) | (g << 8) | b.
    function rentCell(uint16 x, uint16 y, uint24 color) external {
        _rentCell(x, y, color, msg.sender);
    }

    /// @notice Rent a cell using an EIP-2612 permit signature — no prior approve needed.
    function rentCell(
        uint16 x, uint16 y, uint24 color,
        uint256 deadline, uint8 v, bytes32 r, bytes32 s
    ) external {
        IERC20Permit(address(TOKEN)).permit(msg.sender, address(this), rentPrice, deadline, v, r, s);
        _rentCell(x, y, color, msg.sender);
    }

    function _rentCell(uint16 x, uint16 y, uint24 color, address renter) internal {
        if (x >= GRID_SIZE || y >= GRID_SIZE) revert OutOfBounds(x, y);

        uint32 cellId = uint32(y) * GRID_SIZE + x;
        Cell storage cell = cells[cellId];

        if (cell.expiresAt > block.timestamp && cell.renter != renter) {
            revert CellNotAvailable(cellId, cell.expiresAt);
        }

        // forge-lint: disable-next-line(unsafe-typecast)
        uint64 expiresAt = uint64(block.timestamp + rentDuration);
        cell.renter    = renter;
        cell.color     = color;
        cell.expiresAt = expiresAt;

        TOKEN.safeTransferFrom(renter, FAUCET, rentPrice);

        emit CellRented(cellId, renter, expiresAt);
        emit CellColorUpdated(cellId, renter, color);
    }

    /// @notice Update the colour of a cell you currently rent.
    /// @param x     Column, 0–999.
    /// @param y     Row, 0–999.
    /// @param color Packed RGB: (r << 16) | (g << 8) | b.
    function setColor(uint16 x, uint16 y, uint24 color) external {
        if (x >= GRID_SIZE || y >= GRID_SIZE) revert OutOfBounds(x, y);

        uint32 cellId = uint32(y) * GRID_SIZE + x;
        Cell storage cell = cells[cellId];

        if (cell.renter != msg.sender || cell.expiresAt <= block.timestamp) {
            revert NotCellRenter(cellId);
        }

        cell.color = color;

        emit CellColorUpdated(cellId, msg.sender, color);
    }

    function setRentPrice(uint256 newPrice) external onlyOwner {
        if (newPrice == 0) revert InvalidRentPrice();
        emit RentPriceUpdated(rentPrice, newPrice);
        rentPrice = newPrice;
    }

    function setRentDuration(uint256 newDuration) external onlyOwner {
        if (newDuration == 0) revert InvalidRentDuration();
        emit RentDurationUpdated(rentDuration, newDuration);
        rentDuration = newDuration;
    }
}
