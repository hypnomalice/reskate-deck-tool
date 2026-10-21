import json
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import animation
import animation_texture
import creator_engine
import deck_shape
import image_placement


def write_shape(folder, name='Fish', trucks=True):
    """A narrow, notched outline like an SVG2Deck underside layout."""
    folder = Path(folder)
    layout = Image.new('RGBA', (512, 2048), (0, 0, 0, 0))
    poly = [(256, 92), (370, 400), (360, 1700), (440, 1955), (256, 1800), (72, 1955), (152, 1700), (142, 400)]
    ImageDraw.Draw(layout).polygon(poly, fill=(255, 255, 255, 46), outline=(255, 255, 255, 255), width=2)
    layout.save(folder / f'{name}_underside_layout.png')
    profile = dict(format='reskate-deck-shape', version=1, name=name, mask=f'{name}_underside_layout.png',
                   trucks=[dict(u=.5, v=.26, bolts=[[.41, .23], [.59, .23], [.41, .29], [.59, .29]]),
                           dict(u=.5, v=.74, bolts=[[.41, .71], [.59, .71], [.41, .77], [.59, .77]])] if trucks else [])
    path = folder / f'{name}_deck_shape.json'
    path.write_text(json.dumps(profile))
    return path


class DeckShapeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = write_shape(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_profile_loads_mask_bounds_and_trucks(self):
        shape = deck_shape.load(self.path)
        self.assertEqual(shape.name, 'Fish')
        left, top, right, bottom = shape.bounds
        self.assertAlmostEqual(left, 72 / 512, delta=.01)
        self.assertAlmostEqual(top, 92 / 2048, delta=.01)
        self.assertAlmostEqual(right, 441 / 512, delta=.01)
        self.assertAlmostEqual(bottom, 1956 / 2048, delta=.01)
        self.assertEqual(shape.mask.getpixel((256, 1000)), 255)
        self.assertEqual(shape.mask.getpixel((256, 1900)), 0)   # the swallowtail notch
        self.assertEqual([round(t[1], 2) for t in shape.trucks], [.26, .74])

    def test_bare_layout_png_is_a_shape_without_trucks(self):
        shape = deck_shape.load(Path(self.folder.name) / 'Fish_underside_layout.png')
        self.assertEqual(shape.name, 'Fish')
        self.assertEqual(shape.trucks, ())
        self.assertGreater(np.asarray(shape.mask).mean(), 40)

    def test_rejects_non_board_images(self):
        path = Path(self.folder.name) / 'square.png'
        Image.new('L', (512, 512), 255).save(path)
        with self.assertRaises(ValueError):
            deck_shape.load(path)

    def test_standard_deck_placement_is_unchanged(self):
        deck = dict(mode='classic')
        self.assertEqual(deck_shape.placement(deck), dict(region=None, bleed=False))
        image = Image.new('RGB', (300, 900), 'red')
        self.assertEqual(image_placement.frame(image, **deck_shape.placement(deck)).tobytes(),
                         image_placement.frame(image).tobytes())

    def test_artwork_fits_the_outline_and_bleeds_past_it(self):
        deck = dict(mode='classic', shape=str(self.path))
        image = Image.new('RGB', (100, 100), 'red')
        ImageDraw.Draw(image).rectangle((0, 0, 99, 9), fill='blue')
        options = deck_shape.placement(deck)
        x0, y0, x1, y1 = deck_shape.region_pixels(options['region'], (512, 2048))
        framed = image_placement.frame(image, 'Stretch', '#00ff00', **options)
        self.assertEqual(framed.size, (512, 2048))
        self.assertEqual(framed.getpixel(((x0 + x1) // 2, y0 + 2))[:3], (0, 0, 255))
        self.assertEqual(framed.getpixel((5, 5)), (0, 0, 255))      # top edge repeated to the corner
        self.assertEqual(framed.getpixel((5, 2040)), (255, 0, 0))
        plain = image_placement.frame(image, 'Stretch', '#00ff00', region=options['region'], bleed=False)
        self.assertEqual(plain.getpixel((5, 5)), (0, 255, 0))
        deck['fit_to_shape'] = False
        self.assertIsNone(deck_shape.placement(deck)['region'])

    def test_layer_foreground_keeps_transparency_outside(self):
        deck = dict(mode='layers', shape=str(self.path))
        self.assertTrue(deck_shape.placement(deck, 1)['bleed'])
        self.assertFalse(deck_shape.placement(deck, 0)['bleed'])
        front = image_placement.frame(Image.new('RGBA', (50, 50), 'red'), alpha=True, **deck_shape.placement(deck, 0))
        self.assertEqual(front.getpixel((2, 2))[3], 0)

    def test_animation_fits_the_outline(self):
        region = deck_shape.load(self.path).bounds
        frames = tuple(Image.new('RGBA', (200, 200), c) for c in ('red', 'blue'))
        clip = animation.Animation(frames, (100, 200), 0)
        _, meta = animation_texture.atlas(clip, placement={}, region=region)
        x0, _, x1, _ = deck_shape.region_pixels(region, (512, 2048))
        self.assertGreaterEqual(meta['board_x'], x0 - 1)
        self.assertLessEqual(meta['board_x'] + meta['board_w'], x1 + 1)
        still = animation_texture.preview_frame(clip, 0, '#ffffff', {}, region)
        self.assertEqual(still.getpixel((10, 1024)), (255, 255, 255))

    def test_thumbnail_follows_the_outline(self):
        shape = deck_shape.load(self.path)
        art = Image.new('RGB', (512, 2048), 'red')
        thumb = creator_engine.thumbnail(art, art, size=256, shape=shape)
        alpha = np.asarray(thumb.getchannel('A'))
        rounded = np.asarray(creator_engine.thumbnail(art, art, size=256).getchannel('A'))
        self.assertLess(alpha.sum(), rounded.sum())

    def test_shaped_export_builds_a_pack(self):
        art = Path(self.folder.name) / 'art.png'
        Image.new('RGB', (400, 400), 'purple').save(art)
        out = Path(self.folder.name) / 'pack.fbmod'
        creator_engine.export_pack([dict(name='Shaped classic', mode='classic', images=[str(art), str(art)],
                                         shape=str(self.path), placement=[dict(zoom=1, x=0, y=0)] * 2)], out)
        data = out.read_bytes()
        self.assertGreater(len(data), 1_000_000)
        self.assertEqual(struct.unpack_from('<I', data, 20)[0], len(creator_engine.split_mod(data)[1]))


if __name__ == '__main__':
    unittest.main()
