// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

uint256 constant INITIAL_SUPPLY = 1_000_000_000 * 10 ** 18;

contract PlaceToken is ERC20 {
    constructor() ERC20("Place", "PLACE") {
        _mint(msg.sender, INITIAL_SUPPLY);
    }
}
