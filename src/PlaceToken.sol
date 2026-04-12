// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

uint256 constant INITIAL_SUPPLY = 1_000_000_000 * 10 ** 18;

contract PlaceToken is ERC20Permit {
    constructor() ERC20("Place", "PLACE") ERC20Permit("Place") {
        _mint(msg.sender, INITIAL_SUPPLY);
    }
}
