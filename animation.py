from bisect import bisect_right
from dataclasses import dataclass
import math
from pathlib import Path

from PIL import Image, ImageOps


@dataclass
class Animation:
    frames: tuple
    ends_ms: tuple
    loop: int

    @property
    def duration_ms(self):
        return self.ends_ms[-1]

    def frame_index(self, elapsed_ms, speed=1):
        if not math.isfinite(elapsed_ms) or elapsed_ms < 0:
            raise ValueError('Playback time must be finite and non-negative.')
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError('Playback speed must be finite and positive.')
        time = elapsed_ms * speed
        if self.loop and time >= self.duration_ms * self.loop:
            return len(self.frames) - 1
        return bisect_right(self.ends_ms, time % self.duration_ms)

    def board_frame(self, index, size=(512, 2048), background='#ffffff', placement=None, region=None):
        frame = self.frames[index]
        settings = placement or {}
        zoom = float(settings.get('zoom', 1))
        x, y = (float(settings.get(axis, 0)) for axis in ('x', 'y'))
        if not all(math.isfinite(value) for value in (zoom, x, y)) or not .1 <= zoom <= 5 or max(abs(x), abs(y)) > 1:
            raise ValueError('Invalid animation placement.')
        # region: fit inside part of the board (a custom deck outline) instead of all of it
        left, top, right, bottom = region or (0, 0, 1, 1)
        area = (size[0] * (right - left), size[1] * (bottom - top))
        scale = min(1, area[0] / frame.width, area[1] / frame.height) * zoom
        width, height = max(1, round(frame.width * scale)), max(1, round(frame.height * scale))
        frame = frame.resize((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', size, background)
        offset = (round(size[0] * left + (area[0] - width) / 2 + x * area[0]),
                  round(size[1] * top + (area[1] - height) / 2 + y * area[1]))
        canvas.alpha_composite(frame, offset)
        return canvas.convert('RGB')

    def texture_atlas(self, board_size=(512, 2048), max_size=8192):
        if not self.frames or len(self.frames) != len(self.ends_ms):
            raise ValueError('Animation frames and timings do not match.')
        source_size = self.frames[0].size
        if any(frame.size != source_size for frame in self.frames):
            raise ValueError('Animation frames must have matching dimensions.')
        if min(*board_size, max_size) <= 0:
            raise ValueError('Texture dimensions must be positive.')
        scale = min(1, board_size[0] / source_size[0], board_size[1] / source_size[1])
        width, height = (max(1, round(value * scale)) for value in source_size)
        gutter = 2
        cell_w, cell_h = width + gutter * 2, height + gutter * 2
        choices = []
        for columns in range(1, len(self.frames) + 1):
            rows = math.ceil(len(self.frames) / columns)
            atlas_w = 1 << (cell_w * columns - 1).bit_length()
            atlas_h = 1 << (cell_h * rows - 1).bit_length()
            if max(atlas_w, atlas_h) <= max_size:
                choices.append((atlas_w * atlas_h, max(atlas_w, atlas_h), columns, atlas_w, atlas_h))
        if not choices:
            raise ValueError('Animation will not fit in one texture. Shorten the clip or reduce its size.')
        _, _, columns, atlas_w, atlas_h = min(choices)
        texture = Image.new('RGBA', (atlas_w, atlas_h))
        rectangles = []
        for index, source in enumerate(self.frames):
            frame = source.convert('RGBA').resize((width, height), Image.Resampling.LANCZOS)
            x = index % columns * cell_w + gutter
            y = index // columns * cell_h + gutter
            texture.paste(frame, (x, y))
            # Duplicate edge pixels so bilinear filtering cannot pick up the next frame.
            for dx, dy, box in (
                (-gutter, 0, (0, 0, 1, height)), (width, 0, (width-1, 0, width, height)),
                (0, -gutter, (0, 0, width, 1)), (0, height, (0, height-1, width, height)),
                (-gutter, -gutter, (0, 0, 1, 1)), (width, -gutter, (width-1, 0, width, 1)),
                (-gutter, height, (0, height-1, 1, height)), (width, height, (width-1, height-1, width, height)),
            ):
                region = frame.crop(box)
                size = (gutter if region.width == 1 else width, gutter if region.height == 1 else height)
                texture.paste(region.resize(size, Image.Resampling.NEAREST), (x+dx, y+dy))
            rectangles.append((x, y, width, height))
        return texture, {
            'frames': rectangles,
            'ends_ms': list(self.ends_ms),
            'loop': self.loop,
            'board_size': list(board_size),
            'board_rect': [(board_size[0]-width)/2, (board_size[1]-height)/2, width, height],
        }


def load(path, *, max_frames=512, max_pixels=256_000_000):
    frames, ends, elapsed, pixels = [], [], 0, 0
    with Image.open(Path(path)) as image:
        if not getattr(image, 'is_animated', False):
            raise ValueError('Choose an animated GIF, PNG or WebP.')
        loop = int(image.info.get('loop', 0))
        if image.format == 'GIF':
            loop = 1 if 'loop' not in image.info else 0 if loop == 0 else loop + 1
        start = 1 if image.info.get('default_image', False) else 0
        count = image.n_frames - start
        if count > max_frames:
            raise ValueError(f'Animation has {count} frames; shorten it to {max_frames} or fewer.')
        for index in range(start, image.n_frames):
            image.seek(index)
            pixels += image.width * image.height
            if pixels > max_pixels:
                raise ValueError('Animation is too large to decode. Reduce its dimensions or length.')
            duration = float(image.info.get('duration', 100))
            if not math.isfinite(duration) or duration <= 0:
                duration = 100
            elapsed += duration
            frames.append(ImageOps.exif_transpose(image).convert('RGBA').copy())
            ends.append(elapsed)
    return Animation(tuple(frames), tuple(ends), loop)
