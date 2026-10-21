"""Custom deck outlines in board space.

Deck graphics are sampled through the deck's board-space UVs (ReSkateUV1): the
underside is one straight top-down 512 x 2048 tile. A shape mod built with
SVG2Deck uses the same tile, so its outline can be described as a mask over the
tool's existing canvas. Nothing here changes the exported atlas format; shapes
only change where artwork is placed, the preview and the thumbnail.

Accepted files:
  * <name>_deck_shape.json   written by SVG2Deck (outline mask + truck bolts)
  * <name>_underside_layout.png (or any 1:4 mask: alpha, or white on black)
"""
from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

TILE = (512, 2048)
FORMAT = 'reskate-deck-shape'


@dataclass(frozen=True, eq=False)
class DeckShape:
    name: str
    mask: Image.Image           # 'L', TILE sized, 255 on the deck
    trucks: tuple = ()          # ((u, v, ((u, v), ...)), ...) as image fractions
    source: str = ''

    @property
    def bounds(self):
        """Outline bounding box as (left, top, right, bottom) image fractions."""
        box = self.mask.getbbox()
        if not box:
            raise ValueError('The deck shape mask is empty.')
        w, h = self.mask.size
        return (box[0] / w, box[1] / h, box[2] / w, box[3] / h)

    def mask_at(self, size):
        return _scaled(self, tuple(int(v) for v in size))

    def outline_at(self, size, width=2):
        """Thin ring just outside the outline, for drawing the deck edge."""
        mask = self.mask_at(size)
        grown = mask.filter(ImageFilter.MaxFilter(2 * width + 1))
        return Image.fromarray(np.maximum(np.asarray(grown, np.int16) - np.asarray(mask, np.int16), 0)
                               .astype(np.uint8))


@lru_cache(maxsize=16)
def _scaled(shape, size):
    return shape.mask.resize(size, Image.Resampling.BILINEAR)


def _mask_from_image(image):
    image = ImageOps.exif_transpose(image)
    w, h = image.size
    if not w or abs(h / w - 4) > .02:
        raise ValueError(f'A deck shape mask must be a 1:4 board-space image (512 × 2048); this one is {w} × {h}.')
    if 'A' in image.getbands() or image.mode in ('P', 'PA') and 'transparency' in image.info:
        alpha = image.convert('RGBA').getchannel('A')
        lo, hi = alpha.getextrema()
        if lo < hi:   # a real transparency mask, like SVG2Deck's layouts
            mask = alpha.point(lambda a: 255 if a > 0 else 0)
        else:
            mask = image.convert('L').point(lambda v: 255 if v > 24 else 0)
    else:
        mask = image.convert('L').point(lambda v: 255 if v > 24 else 0)
    mask = mask.resize(TILE, Image.Resampling.NEAREST if mask.size == TILE else Image.Resampling.BILINEAR)
    mask = mask.point(lambda v: 255 if v >= 128 else 0)
    if not mask.getbbox():
        raise ValueError('The deck shape mask is empty: draw the deck in white (or opaque) on a black (or transparent) background.')
    return mask


def _fraction(value, label):
    value = float(value)
    if not math.isfinite(value) or not -.5 <= value <= 1.5:
        raise ValueError(f'Deck shape {label} is outside the board.')
    return value


def _profile(path):
    data = json.loads(path.read_text(encoding='utf8'))
    if data.get('format') != FORMAT:
        raise ValueError('This JSON file is not a deck shape profile.')
    if int(data.get('version', 0)) != 1:
        raise ValueError('This deck shape profile needs a newer version of the tool.')
    if not data.get('mask'):
        raise ValueError('The deck shape profile has no outline image next to it. Re-run SVG2Deck.')
    mask_path = (path.parent / data['mask']).resolve()
    if not mask_path.is_file():
        raise ValueError(f'The outline image {data["mask"]} is missing; keep it beside the profile.')
    with Image.open(mask_path) as image:
        mask = _mask_from_image(image)
    trucks = []
    for truck in data.get('trucks') or []:
        bolts = tuple((_fraction(u, 'truck bolt'), _fraction(v, 'truck bolt')) for u, v in truck.get('bolts', []))
        trucks.append((_fraction(truck.get('u', .5), 'truck'), _fraction(truck['v'], 'truck'), bolts))
    trucks.sort(key=lambda t: t[1])
    return DeckShape(str(data.get('name') or path.stem), mask, tuple(trucks), str(path))


@lru_cache(maxsize=8)
def _load(path, stamp):
    path = Path(path)
    if path.suffix.lower() == '.json':
        return _profile(path)
    with Image.open(path) as image:
        mask = _mask_from_image(image)
    name = path.stem
    for suffix in ('_underside_layout', '_deck_shape'):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return DeckShape(name, mask, (), str(path))


def load(path):
    """Load a profile or mask; cached until the file changes."""
    path = Path(path).resolve()
    stat = path.stat()
    profile = None
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf8'))
        if data.get('mask'):
            mask = (path.parent / data['mask'])
            if mask.is_file():
                profile = mask.stat().st_mtime_ns
    return _load(str(path), (stat.st_mtime_ns, stat.st_size, profile))


def for_deck(deck):
    """The deck's shape, or None for the standard popsicle."""
    path = deck.get('shape')
    return load(path) if path else None


def placement(deck, index=0):
    """(region, bleed) keyword arguments for image_placement.frame.

    region is the outline's bounding box when artwork should fit the shape;
    bleed extends edge pixels past it, so parallax and texture filtering never
    reveal the padding colour at the deck edge.
    """
    shape = for_deck(deck)
    if shape is None:
        return dict(region=None, bleed=False)
    region = shape.bounds if deck.get('fit_to_shape', True) else None
    foreground = deck.get('mode') == 'layers' and index == 0
    return dict(region=region, bleed=bool(region) and deck.get('shape_bleed', True) and not foreground)


def bleed(image, region):
    """Repeat the edge pixels of region (fractions) out to the image border."""
    w, h = image.size
    x0, y0, x1, y1 = region_pixels(region, (w, h))
    pixels = np.asarray(image)
    rows = np.clip(np.arange(h), y0, y1 - 1)
    cols = np.clip(np.arange(w), x0, x1 - 1)
    return Image.fromarray(np.ascontiguousarray(pixels[rows][:, cols]), image.mode)


def region_pixels(region, size):
    """Region fractions as an integer (left, top, right, bottom) box, at least one pixel."""
    w, h = size
    x0, y0 = max(0, min(w - 1, round(region[0] * w))), max(0, min(h - 1, round(region[1] * h)))
    x1, y1 = max(x0 + 1, min(w, round(region[2] * w))), max(y0 + 1, min(h, round(region[3] * h)))
    return x0, y0, x1, y1
