// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract PlaceFaucet is Ownable {
    using SafeERC20 for IERC20;

    IERC20 public immutable TOKEN;

    uint256 public claimAmount;
    uint256 public cooldown;

    mapping(address => uint256) public lastClaimed;

    error CooldownNotElapsed(uint256 availableAt);
    error InsufficientFaucetBalance(uint256 available, uint256 required);

    event Claimed(address indexed claimant, uint256 amount);
    event ClaimAmountUpdated(uint256 oldAmount, uint256 newAmount);
    event CooldownUpdated(uint256 oldCooldown, uint256 newCooldown);

    constructor(address token_, uint256 claimAmount_, uint256 cooldown_, address owner_)
        Ownable(owner_)
    {
        TOKEN = IERC20(token_);
        claimAmount = claimAmount_;
        cooldown = cooldown_;
    }

    function claim() external {
        if (lastClaimed[msg.sender] != 0) {
            uint256 availableAt = lastClaimed[msg.sender] + cooldown;
            if (block.timestamp < availableAt) {
                revert CooldownNotElapsed(availableAt);
            }
        }

        uint256 balance = TOKEN.balanceOf(address(this));
        if (balance < claimAmount) {
            revert InsufficientFaucetBalance(balance, claimAmount);
        }

        lastClaimed[msg.sender] = block.timestamp;
        TOKEN.safeTransfer(msg.sender, claimAmount);

        emit Claimed(msg.sender, claimAmount);
    }

    function setClaimAmount(uint256 newAmount) external onlyOwner {
        emit ClaimAmountUpdated(claimAmount, newAmount);
        claimAmount = newAmount;
    }

    function setCooldown(uint256 newCooldown) external onlyOwner {
        emit CooldownUpdated(cooldown, newCooldown);
        cooldown = newCooldown;
    }
}
