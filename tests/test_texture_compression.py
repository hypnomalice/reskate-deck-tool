import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import texture_compression as compression


class TextureCompressionTests(unittest.TestCase):
    def setUp(self):
        compression.clear_cache()

    def tearDown(self):
        compression.clear_cache()

    def image(self):
        return Image.fromarray(np.random.default_rng(18).integers(0, 256, (64, 16, 4), dtype=np.uint8))

    def reference(self, image, profile, mipmaps):
        image = image.convert('RGBA')
        levels = max(image.size).bit_length() - 1 if mipmaps else 1
        pieces = []
        for level in range(levels):
            w, h = max(1, image.width >> level), max(1, image.height >> level)
            mip = image.resize((w, h), Image.Resampling.LANCZOS) if level else image
            if w < 4 or h < 4:
                pad = Image.new('RGBA', (max(4, w), max(4, h)))
                for y in range(pad.height):
                    for x in range(pad.width):
                        pad.putpixel((x, y), mip.getpixel((min(x, w - 1), min(y, h - 1))))
                mip = pad
            for y in range(0, mip.height, 256):
                strip = mip.crop((0, y, mip.width, min(y + 256, mip.height)))
                pieces.append(compression._compress((strip.tobytes(), strip.width, strip.height, profile)))
        return b''.join(pieces)

    def test_parallel_preserves_transparent_pixels_mips_and_edge_padding(self):
        image = self.image()
        for profile in ('fast', 'slow'):
            for mips in (False, True):
                expected = self.reference(image, profile, mips)
                compression.clear_cache()
                self.assertEqual(compression.encode(image, profile=profile, mipmaps=mips, workers=4), expected)

    def test_parallel_preserves_multiple_strips_in_order(self):
        image = self.image().resize((32, 1024))
        self.assertEqual(compression.encode(image, profile='fast', workers=4), self.reference(image, 'fast', True))

    def test_cache_invalidates_pixels_profile_and_mips(self):
        image = self.image()
        with patch.object(compression, '_compress', wraps=compression._compress) as calls:
            a = compression.encode(image, profile='fast', mipmaps=False)
            count = calls.call_count
            self.assertEqual(compression.encode(image.copy(), profile='fast', mipmaps=False), a)
            self.assertEqual(calls.call_count, count)
            changed = image.copy(); changed.putpixel((0, 0), (255, 0, 0, 0))
            compression.encode(changed, profile='fast', mipmaps=False)
            self.assertGreater(calls.call_count, count); count = calls.call_count
            compression.encode(image, profile='slow', mipmaps=False)
            self.assertGreater(calls.call_count, count); count = calls.call_count
            compression.encode(image, profile='fast', mipmaps=True)
            self.assertGreater(calls.call_count, count)

    def test_cache_budget_evicts_old_textures(self):
        with patch.object(compression, '_CACHE_LIMIT', 300):
            for colour in ('red', 'green', 'blue'):
                compression.encode(Image.new('RGBA', (16, 16), colour), mipmaps=False)
                self.assertLessEqual(compression._cache_bytes, 300)
            self.assertEqual(len(compression._cache), 1)

    def test_failed_export_does_not_cache_partial_texture(self):
        def interrupted(message):
            raise InterruptedError('cancelled')
        with self.assertRaises(InterruptedError):
            compression.encode(self.image(), interrupted, profile='fast')
        self.assertFalse(compression._cache)
        self.assertEqual(compression.encode(self.image(), profile='fast'), self.reference(self.image(), 'fast', True))
