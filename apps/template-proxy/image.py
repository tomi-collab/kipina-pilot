from __future__ import annotations

import re
from typing import Any


SEED_RE = re.compile(r"[^A-Za-z0-9-]+")
MIN_SIZE = 100
MAX_SIZE = 1200
DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 400


class ImageError(Exception):
    status = 400
    error = "validation_error"


def _parse_size(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        size = int(value)
    except ValueError as exc:
        raise ImageError("width and height must be integers") from exc
    if size < MIN_SIZE or size > MAX_SIZE:
        raise ImageError("width and height must be between 100 and 1200")
    return size


def _sanitize_seed(seed: str) -> str:
    sanitized = SEED_RE.sub("", seed.strip())[:60]
    if not sanitized:
        raise ImageError("seed is required and must contain letters, numbers or hyphens")
    return sanitized


def get_random_image(seed: str, width: str | None = None, height: str | None = None) -> dict[str, Any]:
    sanitized_seed = _sanitize_seed(seed)
    parsed_width = _parse_size(width, DEFAULT_WIDTH)
    parsed_height = _parse_size(height, DEFAULT_HEIGHT)
    return {
        "image_url": f"https://picsum.photos/seed/{sanitized_seed}/{parsed_width}/{parsed_height}",
        "width": parsed_width,
        "height": parsed_height,
        "note": "Satunnainen valokuva (sisältö ei liity aiheeseen). Sama seed antaa saman kuvan.",
        "source": "Lorem Picsum / Unsplash",
    }
