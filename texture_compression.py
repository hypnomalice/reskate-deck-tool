"""Byte-identical BC7 compression with bounded parallel work and an in-memory cache."""
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
import threading

import ispc_texcomp as tc
from PIL import Image

_CACHE_LIMIT = 64 * 1024 * 1024
_cache = OrderedDict()
_cache_bytes = 0
_lock = threading.Lock()


def clear_cache():
    global _cache_bytes
    with _lock:
        _cache.clear()
        _cache_bytes = 0


def _key(image, profile, mipmaps):
    return (image.size, profile, bool(mipmaps), hashlib.sha256(image.tobytes()).digest())


def _get(key):
    with _lock:
        value = _cache.get(key)
        if value is not None:
            _cache.move_to_end(key)
        return value


def _put(key, value):
    global _cache_bytes
    if len(value) > _CACHE_LIMIT:
        return
    with _lock:
        previous = _cache.pop(key, None)
        if previous is not None:
            _cache_bytes -= len(previous)
        _cache[key] = value
        _cache_bytes += len(value)
        while _cache_bytes > _CACHE_LIMIT:
            _, removed = _cache.popitem(last=False)
            _cache_bytes -= len(removed)


def _compress(job):
    pixels, width, height, profile = job
    # Give each call its own immutable settings object.
    return tc.compress_blocks_bc7(tc.RGBASurface(pixels, width, height, width * 4),
                                 tc.BC7EncSettings.from_profile(profile))


def thumbnail(image):
    image = image.convert('RGBA')
    key = _key(image, 'alpha_basic', False)
    cached = _get(key)
    if cached is not None:
        return cached
    result = _compress((image.tobytes(), image.width, image.height, 'alpha_basic'))
    _put(key, result)
    return result


def encode(image, progress=lambda message: None, *, profile='slow', mipmaps=True, workers=None):
    image = image.convert('RGBA')
    key = _key(image, profile, mipmaps)
    cached = _get(key)
    if cached is not None:
        progress('Reusing unchanged texture...')
        return cached
    width, height = image.size
    levels = max(width, height).bit_length() - 1 if mipmaps else 1
    total = sum(max(1, ((width >> n) + 3) // 4) * max(1, ((height >> n) + 3) // 4) * 16
                for n in range(levels))
    completed = 0
    parts = []
    count = max(1, min(4, (os.cpu_count() or 2) - 1)) if workers is None else max(1, workers)
    # At most two strips per worker are queued, including large GIF atlases.
    with ThreadPoolExecutor(max_workers=count, thread_name_prefix='deck-bc7') as pool:
        for level in range(levels):
            progress(f'Preparing texture detail {level + 1} of {levels}...')
            w, h = max(1, width >> level), max(1, height >> level)
            mip = image.resize((w, h), Image.Resampling.LANCZOS) if level else image
            if w < 4 or h < 4:
                pad = Image.new('RGBA', (max(4, w), max(4, h)))
                for y in range(pad.height):
                    for x in range(pad.width):
                        pad.putpixel((x, y), mip.getpixel((min(x, w - 1), min(y, h - 1))))
                mip = pad
            pending = deque()
            strips = []
            def collect():
                nonlocal completed
                compressed = pending.popleft().result()
                strips.append(compressed)
                completed += len(compressed)
                progress(f'Compressing texture: {completed / total:.0%} (detail {level + 1}/{levels})')
            for y in range(0, mip.height, 256):
                strip = mip.crop((0, y, mip.width, min(y + 256, mip.height)))
                pending.append(pool.submit(_compress, (strip.tobytes(), strip.width, strip.height, profile)))
                if len(pending) >= count * 2:
                    collect()
            while pending:
                collect()
            data = b''.join(strips)
            assert len(data) == max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16
            parts.append(data)
    result = b''.join(parts)
    assert len(result) == total
    _put(key, result)
    return result
