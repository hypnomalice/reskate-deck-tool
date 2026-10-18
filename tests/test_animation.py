import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import animation
import animation_texture


class AnimatedDeckTests(unittest.TestCase):
    def setUp(self):
        self.clip = animation.Animation(
            (Image.new('RGBA', (80, 40), 'red'), Image.new('RGBA', (80, 40), 'blue')),
            (80, 200), 0)

    def test_gif_keeps_frame_times(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'clip.gif'
            self.clip.frames[0].save(path, save_all=True, append_images=self.clip.frames[1:],
                                     duration=[80, 120], loop=0)
            loaded = animation.load(path)
            self.assertEqual(loaded.ends_ms, (80, 200))
            self.assertEqual([loaded.frame_index(t) for t in (0, 79, 80, 199, 200)], [0, 0, 1, 1, 0])

    def test_metadata_and_aspect_ratio(self):
        texture, info = animation_texture.atlas(self.clip)
        self.assertEqual((info['board_w'], info['board_h']), (80, 40))
        self.assertEqual((info['board_x'], info['board_y']), (216, 1004))
        for i, field in enumerate(animation_texture.FIELDS):
            self.assertEqual(animation_texture.read_word(texture.getpixel((i*32+16, 96))), info[field])
        self.assertEqual(animation_texture.read_word(texture.getpixel((2, 160))), 8)
        self.assertEqual(animation_texture.read_word(texture.getpixel((6, 160))), 20)

    def test_placement_crops_at_board_edge(self):
        _, info = animation_texture.atlas(self.clip, placement=dict(zoom=2, x=.5, y=0))
        self.assertEqual((info['board_x'], info['board_w'], info['board_h']), (432, 80, 80))

    def test_export_limits(self):
        with self.assertRaisesRegex(ValueError, '128'):
            animation_texture.atlas(animation.Animation(self.clip.frames*65, tuple(range(1, 131)), 0))
        with self.assertRaisesRegex(ValueError, '40.95'):
            animation_texture.atlas(animation.Animation(self.clip.frames, (100, 40960), 0))
        with self.assertRaisesRegex(ValueError, 'outside'):
            animation_texture.atlas(self.clip, placement=dict(x=1, y=0, zoom=1))


if __name__ == '__main__':
    unittest.main()
