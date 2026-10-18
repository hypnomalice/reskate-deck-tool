"""Full-width planes for continuous foreground/background parallax.

RGB stores transparency explicitly because the game's graphic colour binding
does not reliably expose alpha. This layout is shared with the shader.
"""
from functools import lru_cache

from PIL import Image, ImageDraw

import depth_views

ATLAS_SIZE = (512, 4096)
PLANE_HEIGHT = 1344
HEADER_HEIGHT = 64


def encode_linear(value):
    encoded = 12.92 * value if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055
    return round(255 * encoded)


@lru_cache(maxsize=1)
def _premultiply_table():
    linear = [v / 255 / 12.92 if v <= 10 else ((v / 255 + .055) / 1.055) ** 2.4
              for v in range(256)]
    return bytes(encode_linear(linear[color] * alpha / 255)
                 for alpha in range(256) for color in range(256))


def pack(foreground, background, strength=.08, background_motion=.5,
         lens_texture=.35, reverse=False):
    strength = depth_views._unit_interval(strength, 'Depth strength')
    background_motion = depth_views._unit_interval(background_motion, 'Background motion')
    lens_texture = depth_views._unit_interval(lens_texture, 'Lens texture')
    if foreground.size != background.size:
        raise ValueError('Foreground and background must have matching dimensions.')
    foreground = foreground.convert('RGBA')
    background = background.convert('RGB')
    rgba = foreground.tobytes()
    table = _premultiply_table()
    pixels = bytes(table[rgba[index + 3] * 256 + rgba[index + channel]]
                   for index in range(0, len(rgba), 4) for channel in range(3))
    colour = Image.frombytes('RGB', foreground.size, pixels)
    mask = foreground.getchannel('A').point([encode_linear(a / 255) for a in range(256)]).convert('RGB')
    atlas = Image.new('RGB', ATLAS_SIZE)
    for index, plane in enumerate((colour, background, mask)):
        depth_views._paste_view_tile(atlas, plane, (0, HEADER_HEIGHT + index * PLANE_HEIGHT),
                                     (ATLAS_SIZE[0], PLANE_HEIGHT), 0)
    draw = ImageDraw.Draw(atlas)
    for index, marker in enumerate(((255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0))):
        draw.rectangle((index * 128, 0, index * 128 + 127, 63), fill=marker)
    draw.rectangle((0, 48, 127, 63), fill=(0, 255, round(lens_texture * 255)))
    draw.rectangle((128, 48, 255, 63),
                   fill=(encode_linear(strength), encode_linear(background_motion), 255 if reverse else 0))
    return atlas
