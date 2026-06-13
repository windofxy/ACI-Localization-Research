from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PackedLayout:
    positions: list[tuple[int, int]]
    used_width: int
    used_height: int
    mode: str


def estimate_required_area(sizes: list[tuple[int, int]]) -> int:
    return sum(width * height for width, height in sizes)


def validate_pack_capacity(
    sizes: list[tuple[int, int]],
    max_width: int,
    max_height: int,
    context: str,
) -> None:
    if max_width <= 0 or max_height <= 0:
        raise ValueError("Atlas size must be greater than zero.")

    for width, height in sizes:
        if width > max_width or height > max_height:
            raise ValueError(
                f"{context} contains a glyph rectangle {width}x{height} that exceeds the atlas size "
                f"{max_width}x{max_height}."
            )

    required_area = estimate_required_area(sizes)
    atlas_area = max_width * max_height
    if required_area > atlas_area:
        raise ValueError(
            f"{context} cannot fit inside {max_width}x{max_height}. "
            f"Minimum required area is {required_area}, atlas area is {atlas_area}."
        )


def try_pack_rectangles_shelf(
    sizes: list[tuple[int, int]],
    max_width: int,
    max_height: int,
) -> PackedLayout | None:
    positions: list[tuple[int, int]] = []
    cursor_x = 0
    cursor_y = 0
    row_height = 0
    used_width = 0
    used_height = 0

    for width, height in sizes:
        if cursor_x > 0 and cursor_x + width > max_width:
            cursor_y += row_height
            cursor_x = 0
            row_height = 0

        if cursor_y + height > max_height:
            return None

        positions.append((cursor_x, cursor_y))
        cursor_x += width
        row_height = max(row_height, height)
        used_width = max(used_width, cursor_x)
        used_height = max(used_height, cursor_y + height)

    return PackedLayout(
        positions=positions,
        used_width=used_width,
        used_height=used_height,
        mode="shelf",
    )


def pack_rectangles(
    sizes: list[tuple[int, int]],
    max_width: int,
    max_height: int,
    context: str,
) -> PackedLayout:
    if not sizes:
        return PackedLayout(positions=[], used_width=0, used_height=0, mode="empty")

    validate_pack_capacity(sizes, max_width, max_height, context)

    shelf_layout = try_pack_rectangles_shelf(sizes, max_width, max_height)
    if shelf_layout is not None:
        return shelf_layout

    required_area = estimate_required_area(sizes)
    atlas_area = max_width * max_height
    raise ValueError(
        f"{context} failed inside {max_width}x{max_height} using shelf packing. "
        f"Minimum required area is {required_area}, atlas area is {atlas_area}. "
        "Try a larger atlas."
    )
