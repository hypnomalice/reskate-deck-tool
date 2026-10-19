import numpy as np
from PIL import Image


def views(image, depth, strength=.04, convergence=.5, progress=lambda message: None):
    """Interactive approximation; exported views still use the depth-buffer renderer."""
    size = (252, 1004)
    rgb = np.asarray(image.convert('RGB').resize(size, Image.Resampling.LANCZOS), dtype=np.float32)
    z = np.asarray(depth.convert('L').resize(size, Image.Resampling.BILINEAR), dtype=np.float32) / 255
    height, width = z.shape
    x = np.broadcast_to(np.arange(width, dtype=np.float32), z.shape)
    rows = np.arange(height)[:, None]

    def sample(plane, coords):
        coords = np.clip(coords, 0, width - 1)
        left = coords.astype(np.int32)
        right = np.minimum(left + 1, width - 1)
        mix = coords - left
        if plane.ndim == 3:
            mix = mix[..., None]
        return plane[rows, left] * (1 - mix) + plane[rows, right] * mix

    result = []
    for index in range(8):
        progress(f'Preparing preview {index + 1} of 8')
        scale = (index * 2 / 7 - 1) * strength * width
        source = x.copy()
        for _ in range(3):
            source = x - scale * (sample(z, source) - convergence)
        result.append(Image.fromarray(np.clip(np.rint(sample(rgb, source)), 0, 255).astype(np.uint8)))
    return result
