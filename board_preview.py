"""Preview-only calibration for the standard donor deck. Never alters exports."""
import math
from PIL import Image

# Measured underside primary-UV coverage on the standard popsicle donor.
# The released effect samples frac(primaryU * 2), frac(primaryV); its atlas
# sampling already skips the shader header. Do not add that header a second time.
# These aggregate calibration values contain no game mesh or texture data.
ARTWORK_REGION = (.031, .07715, .961, .99512)


def map_artwork(image, size=None):
    """Place the shader's normalised artwork on the standard board template.

    Run once after effect/animation evaluation, including live placement. Keep
    source artwork, saved positions and exported atlases unchanged. Other deck
    meshes can have different UVs; this is not a universal shape calibration.
    """
    w, h = image.size
    left, top, right, bottom = ARTWORK_REGION
    return image.resize(size or image.size, Image.Resampling.BICUBIC,
                        box=(left*w, top*h, right*w, bottom*h))


def surface(u, v):
    """Authored, procedural popsicle approximation, not an extracted game mesh."""
    cap = .12
    end = max(0., cap-v, v-(1-cap))/cap
    # Keep the endpoint quad invertible for the texture projection (subpixel tip).
    half_width = .5*math.sqrt(max(.0001, 1-end*end))
    x = (u*2-1)*half_width
    y = (v-.5)*3.88
    kick = max(0., (abs(v-.5)-.29)/.21)
    z = .22*kick*kick + .055*(2*x)**2
    return x, y, z
