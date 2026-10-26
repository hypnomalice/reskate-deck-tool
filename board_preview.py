"""Visible-artwork calibration for previews and automatic deck thumbnails."""
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


# Procedural dimensions fitted to the supplied plain-control silhouette and side view.
DECK_LENGTH = 3.82
CAMERA_DISTANCE = 24.0
NOSE_CAP, NOSE_POWER = .5, 9.2
TAIL_CAP, TAIL_POWER = .175, 1.75
NOSE_KICK, TAIL_KICK = .16, .13
PIVOT_DEPTH = .08
TRUCK_CENTRES = (.228, .774)  # axle positions along the visible deck
PLATE_CENTRES = (.242, .759)
PLATE_WIDTH, PLATE_LENGTH = .28, .083
BOLT_HALF_WIDTH, BOLT_HALF_LENGTH = .112, .027


def surface(u, v):
    """Procedural standard-deck profile, calibrated from aggregate capture measurements."""
    end = max(0., 1-v/NOSE_CAP) if v < .5 else max(0., 1-(1-v)/TAIL_CAP)
    power = NOSE_POWER if v < .5 else TAIL_POWER
    half_width = .5*math.sqrt(max(.0001, 1-end**power))
    x = (u*2-1)*half_width
    y = (v-.5)*DECK_LENGTH
    kick = NOSE_KICK*max(0.,(.24-v)/.24)**2 + TAIL_KICK*max(0.,(v-.77)/.23)**2
    z = PIVOT_DEPTH + kick + .055*(2*x)**2
    return x, y, z


# Orbit-to-effect calibration for the authored preview shape. The effect slider is
# a transition range, not a measured physical camera angle in every game mesh.
def orbit_angle(yaw):
    return math.sin(math.radians(max(-70., min(70., yaw)))) / math.sin(math.radians(70.))


def orbit_yaw(angle):
    return math.degrees(math.asin(max(-1., min(1., angle)) * math.sin(math.radians(70.))))


DECK_THICKNESS = .035  # authored template: about 7 mm for an 8-inch-wide deck


def texture_uv(u, v):
    """Planar artwork follows physical board width, rather than stretching at tips."""
    x, _, _ = surface(u, v)
    return x+.5, v


def rotate(x, y, z, yaw, pitch):
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    x, z = x*math.cos(yaw)+z*math.sin(yaw), -x*math.sin(yaw)+z*math.cos(yaw)
    return x, y*math.cos(pitch)-z*math.sin(pitch), y*math.sin(pitch)+z*math.cos(pitch)

# Calibrated only for the native lens paths; the 2D effect slider keeps its full range.
LENS_VIEW_PROFILE = (-.21, .10, -.83)  # bias, cross-deck curvature, yaw response
