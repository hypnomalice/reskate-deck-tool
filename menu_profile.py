"""Aggregate menu-capture calibration; contains no game textures or mesh data.

Fitted against the user's 2026-10-26 standard-deck rotations, captured in HDR and
converted to SDR by ReSkate. This profile describes that menu setup, not all maps.
"""
import numpy as np

COLOUR = (10.0, 0.88465232, 0.92663784, 0.83530621, 0.32995674)
LIGHT_VIEWS = ((-61.875, 2.39468488, 0.0213971, 0.184), (-28.125, 2.18368152, 0.01689165, 0.45), (0.0, 1.98243488, 0.0121971, 0.404), (28.125, 1.33978152, 0.00441165, 0.968), (61.875, 0.87561885, 0.0024, 0.63645148))

def response(rgb, u, yaw, illumination=1., emission=None):
    """Measured diffuse/reflection field and smooth highlight colour compression."""
    power, peak, green, blue, mixing = COLOUR
    data=np.asarray(LIGHT_VIEWS,dtype=np.float32)
    gain, floor, reflection=(float(np.interp(yaw,data[:,0],data[:,i])) for i in (1,2,3))
    # The patches constrain this cross-deck interval; avoid extrapolating an
    # unmeasured bright stripe onto the rim.
    specular=floor+reflection*np.clip(u,.22,.77)**power
    hdr=(rgb*gain+specular[...,None])*np.asarray(illumination)[...,None]
    peak_field=peak
    if emission is not None:
        emission=np.maximum(np.asarray(emission,dtype=np.float32),0)*EMISSION_EXPOSURE
        hdr=hdr+emission
        amount=1-np.exp(-np.mean(emission,axis=-1,keepdims=True))
        peak_field=peak+(EMISSION_WHITE-peak)*amount
        mixing=mixing+(EMISSION_MIXING-mixing)*amount
    luma=np.array([.2126,.7152,.0722],dtype=np.float32)
    # A rank-one colour compression and its analytic inverse. This also lets
    # emission keep its calibrated highlight chroma without changing albedo.
    mixed=hdr*(1-mixing)+np.sum(hdr*luma,axis=-1,keepdims=True)*mixing
    compressed=peak_field*(1-np.exp(-mixed*np.array([1,green,blue],dtype=np.float32)))
    restored=(compressed-mixing*np.sum(compressed*luma,axis=-1,keepdims=True))/(1-mixing)
    return np.clip(restored,0,1)

# Capture exposure calibration, independent of the shader's 32x authored gain.
EMISSION_EXPOSURE = 0.706
EMISSION_WHITE = 0.93
EMISSION_MIXING = 0.15
