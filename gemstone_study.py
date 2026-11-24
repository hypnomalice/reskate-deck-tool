"""Private artwork-free gemstone study data and matching CPU diagnostics.

Surface normals/roughness and internal optical domains are separate maps.
Crystal cut maps are deliberately not handled here.
"""
from functools import lru_cache
import numpy as np
from PIL import Image, ImageFilter
import layer_atlas


def _encode(channels):
    table = [layer_atlas.encode_linear(i / 255) for i in range(256)]
    return Image.merge('RGB', [Image.fromarray(
        np.uint8(np.rint(np.clip(c, 0, 1) * 255)), 'L').point(table)
        for c in channels])


def _noise(rng, shape, blur=0):
    im = Image.fromarray(rng.integers(0, 256, shape, dtype=np.uint8), 'L')
    im = im.resize((512, 2048), Image.Resampling.BICUBIC)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, dtype=float) / 255


@lru_cache(maxsize=2)
def transport_maps(finish):
    if finish not in ('moonstone', 'opal'):
        raise ValueError('Study maps apply only to opal and moonstone')
    rng = np.random.default_rng(8261)
    y, x = np.mgrid[0:2048, 0:512]
    u, v = x / 511, y / 2047
    grain = _noise(rng, (120, 30), 2.2)
    fine = _noise(rng, (420, 105), .8)
    # Very shallow polished-stone irregularity over a broad curved profile.
    # Derivatives alter highlights; they never become the colour pattern.
    dy, dx = np.gradient(grain * .65 + fine * .35)
    nx = (u - .5) * .70 + dx * .18
    ny = (v - .5) * .17 + dy * .18
    rough = .045 + fine * .018
    surface = _encode((.5 + nx * .5, .5 + ny * .5, rough))
    if finish == 'moonstone':
        broad = _noise(rng, (6, 3), 16)
        # Mostly aligned layers: a coherent sheen rather than blue islands.
        ox = .5 + (u - .5) * .38 + (broad - .5) * .025
        oy = .5 + (v - .5) * .09 + (broad - .5) * .02
        optical = _encode((ox, oy, broad))
    else:
        # Small irregular chips, with most of the stone left quiet.
        cols, rows = 38, 152
        centres = rng.uniform(.18, .82, (rows, cols, 2))
        attrs = rng.uniform(.12, .88, (rows, cols, 2))
        active = rng.random((rows, cols)) < .24
        spacing = np.where(active, rng.uniform(.12, .97, (rows, cols)), 0)
        xx, yy = u * cols, v * rows
        ix, iy = np.floor(xx).astype(int), np.floor(yy).astype(int)
        distance = np.full(u.shape, np.inf)
        ox = np.zeros(u.shape); oy = np.zeros(u.shape); seed = np.zeros(u.shape)
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                cx, cy = ix + i, iy + j
                ax, ay = cx % cols, cy % rows
                point = centres[ay, ax]
                dist = (xx - cx - point[..., 0]) ** 2 + (yy - cy - point[..., 1]) ** 2
                take = dist < distance
                distance[take] = dist[take]
                ox[take] = attrs[ay, ax, 0][take]
                oy[take] = attrs[ay, ax, 1][take]
                seed[take] = spacing[ay, ax][take]
        optical = _encode((ox, oy, seed))
    return surface, optical


def response(finish, optical, view_x, view_y=0):
    """CPU diagnostic for the same angular model used in the study shader.

    A fixed representative light is used for the internal approximation;
    the game's native lighting supplies outer surface reflections separately.
    """
    data = np.asarray(optical, dtype=float) / 255
    f = np.where(data <= .04045, data / 12.92, ((data + .055) / 1.055) ** 2.4)
    fx, fy, seed = f[..., 0] * 2 - 1, f[..., 1] * 2 - 1, f[..., 2]
    hx, hy, hz = view_x + .28, view_y + .16, 2
    hn = np.sqrt(hx * hx + hy * hy + hz * hz)
    nn = np.sqrt(1 + fx * fx + fy * fy)
    q = np.clip((fx * hx + fy * hy + hz) / (hn * nn), 0, 1)
    surface = np.asarray(transport_maps(finish)[0], dtype=float) / 255
    surface = np.where(surface <= .04045, surface / 12.92, ((surface + .055) / 1.055) ** 2.4)
    sx, sy = surface[..., 0] * 2 - 1, surface[..., 1] * 2 - 1
    sn = np.sqrt(1 + sx * sx + sy * sy)
    cq = np.clip((sx * hx + sy * hy + hz) / (hn * sn), 0, 1)
    polish = .055 * np.exp(-((cq - 1) / .018) ** 2) + .25 * np.exp(-((cq - 1) / .0018) ** 2)
    if finish == 'moonstone':
        glow = np.exp(-((q - 1) / .008) ** 2)
        rgb = np.array((.26, .255, .235)) + glow[..., None] * np.array((.005, .055, .18))
        return rgb + polish[..., None]
    wave = (430 + seed * 300) * np.sqrt(np.maximum(.1, 1 - .48 * (1 - q * q)))
    gate = np.where(seed > .075, np.exp(-((q - (.93 + seed * .04)) / .035) ** 2), 0)
    colours = [np.exp(-((wave - centre) / width) ** 2)
               for centre, width in ((615, 44), (540, 34), (463, 29))]
    return np.array((.065, .080, .090)) + np.stack(colours, -1) * gate[..., None] * .28 + polish[..., None]
