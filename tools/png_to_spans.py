#!/usr/bin/env python3
"""Convert a purple-on-black image into SGI-style alternating span data."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


PURPLE = (75, 0, 131)


def split_run(length: int) -> list[int]:
    """Split a run into u8 chunks without changing skip/draw state."""
    values: list[int] = []
    while length > 255:
        values.extend((255, 0))
        length -= 255
    values.append(length)
    return values


def encode_row(bits: list[bool]) -> list[int]:
    """Encode a row as alternating skip/draw lengths, starting with skip."""
    values: list[int] = []
    state = False
    x = 0
    width = len(bits)

    while x < width:
        if bits[x] != state:
            values.append(0)
            state = not state
            continue

        end = x + 1
        while end < width and bits[end] == state:
            end += 1

        values.extend(split_run(end - x))
        state = not state
        x = end

    if sum(values) != width:
        raise RuntimeError("encoded row width mismatch")

    return values


def is_logo_pixel(pixel: tuple[int, int, int]) -> bool:
    """Select purple artwork and reject the near-black background."""
    red, green, blue = pixel
    return (
        blue > 10
        and blue - red > 5
        and blue - green > 5
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--symbol", default="ultraviolentlogo")
    parser.add_argument(
        "--mask-output",
        type=Path,
        help="optional exact two-color preview PNG",
    )
    args = parser.parse_args()

    image = Image.open(args.input).convert("RGB")
    image = image.resize(
        (args.width, args.height),
        Image.Resampling.LANCZOS,
    )

    pixels = image.load()
    mask: list[list[bool]] = [
        [
            is_logo_pixel(pixels[x, y])
            for x in range(args.width)
        ]
        for y in range(args.height)
    ]

    if args.mask_output:
        preview = Image.new("RGB", (args.width, args.height), (0, 0, 0))
        preview_pixels = preview.load()
        for y, row in enumerate(mask):
            for x, enabled in enumerate(row):
                if enabled:
                    preview_pixels[x, y] = PURPLE
        preview.save(args.mask_output)

    # The project writes a bottom-up BMP, so encode PNG rows bottom-to-top.
    rows = [
        encode_row(mask[y])
        for y in range(args.height - 1, -1, -1)
    ]

    output: list[str] = [
        '#include "types.h"',
        "",
        "/* Generated file: do not edit by hand. */",
        f"const u8 {args.symbol}[] = {{",
    ]

    for row_number, values in enumerate(rows):
        encoded = ", ".join(f"0x{value:02x}" for value in values)
        output.append(
            f"    /* {row_number:3d} - {len(values):2d} */ "
            f"{encoded},"
        )

    output.append("};")
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
