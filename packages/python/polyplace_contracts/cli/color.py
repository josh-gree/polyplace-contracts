"""Color parsing for the polyplace CLI."""

from __future__ import annotations


def parse_color(value: str) -> int:
    """Parse '#rrggbb', 'rrggbb', or '0xrrggbb' into a uint24 int."""
    s = value.strip().lower()
    if s.startswith("#"):
        s = s[1:]
    elif s.startswith("0x"):
        s = s[2:]
    if len(s) != 6:
        raise ValueError(f"color must be 6 hex digits, got {value!r}")
    return int(s, 16)
