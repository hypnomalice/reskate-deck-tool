"""CPU preview of the export shader's atlas sampling, before game lighting."""
import numpy as np
from PIL import Image


def linear(rgb):
    rgb = np.asarray(rgb, dtype=np.float32) / 255
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def display(rgb):
    rgb = np.clip(rgb, 0, 1)
    encoded = np.where(rgb <= .0031308, rgb * 12.92, 1.055 * rgb ** (1 / 2.4) - .055)
    return Image.fromarray(np.rint(encoded * 255).astype(np.uint8))


class AtlasPreview:
    def __init__(self, atlas, mode):
        self.pixels = linear(atlas.convert('RGB'))
        self.mode = mode
        self.height, self.width = self.pixels.shape[:2]
        self.settings = self.sample(.125, 56 / 4096)
        self.motion = self.sample(.375, 56 / 4096)
        self.cached_size, self.cached_samples = None, None

    def set_lens_strength(self, value):
        self.settings[2] = float(linear(round(np.clip(value, 0, 1) * 255)))

    def sample(self, u, v):
        x, y = np.broadcast_arrays(np.asarray(u) * self.width - .5,
                                   np.asarray(v) * self.height - .5)
        x = np.clip(x, 0, self.width - 1)
        y = np.clip(y, 0, self.height - 1)
        x0, y0 = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
        x1, y1 = np.minimum(x0 + 1, self.width - 1), np.minimum(y0 + 1, self.height - 1)
        tx, ty = (x - x0).astype(np.float32)[..., None], (y - y0).astype(np.float32)[..., None]
        top = self.pixels[y0, x0] * (1 - tx) + self.pixels[y0, x1] * tx
        bottom = self.pixels[y1, x0] * (1 - tx) + self.pixels[y1, x1] * tx
        return top * (1 - ty) + bottom * ty

    def render(self, angle, size=(210, 840), region=(0, 0, 1, 1)):
        width, height = size
        u = (np.arange(width, dtype=np.float32)[None, :] + .5) / width
        v = (np.arange(height, dtype=np.float32)[:, None] + .5) / height
        left, top, right, bottom = region
        u = left + u * (right - left)
        v = top + v * (bottom - top)
        angle = float(np.clip(angle, -1, 1))
        phase = np.mod(u * 112, 1) - .5
        sample_key = (size, region)
        if self.cached_size != sample_key:
            if self.mode == 'classic':
                self.cached_samples = (self.sample(u, 64 / 4096 + v * 1984 / 4096),
                                       self.sample(u, .5 + v * .5))
            elif self.mode == 'layers':
                plane_u = (np.arange(512,dtype=np.float32)[None,:]+.5)/512
                self.cached_samples = tuple(self.sample(plane_u, offset / 4096 + v * 1340 / 4096)
                                            for offset in (66,1410,2754))
            else:
                tiles = [self.sample(index%2*.5+2/512+u*252/512,
                                     66/4096+(index//2)*1008/4096+v*1004/4096)
                         for index in range(8)]
                self.cached_samples = np.stack(tiles,axis=1).transpose(2,1,0,3)
            self.cached_size = sample_key
        if self.mode == 'classic':
            t = np.clip((angle * .22 - phase * .2) * 12.5 + .5, 0, 1)
            weight = .02 + .96 * t * t * (3 - 2 * t)
            a, b = self.cached_samples
            return display(b + (a - b) * weight[..., None])
        position = np.clip((angle + 1) * 3.5 - phase * .4 * self.settings[2], 0, 7)
        if self.mode == 'layers':
            direction = -1 if self.motion[2] > .5 else 1
            movement = (position / 3.5 - 1) * direction * self.motion[0]
            front_u = u - movement * (1 - self.motion[1])
            back_u = np.clip(u + movement * self.motion[1], 0, 1)
            inside = ((front_u >= 0) & (front_u <= 1))[..., None]
            front_u = np.clip(front_u, 0, 1)
            def columns(plane, coords):
                x = np.clip(coords[0]*512-.5,0,511)
                first = np.floor(x).astype(np.int32)
                weight = (x-first).astype(np.float32)[None,:,None]
                return plane[:,first]*(1-weight)+plane[:,np.minimum(first+1,511)]*weight
            a, b, mask = self.cached_samples
            front = columns(a,front_u)*inside
            back = columns(b,back_u)
            coverage = columns(mask,front_u)[...,:1]*inside
            return display(front + back * (1 - coverage))
        first = np.floor(position)
        second = np.minimum(first + 1, 7)
        weight = (position - first)[..., None]
        def tile(index):
            return self.cached_samples[np.arange(width),index[0].astype(np.int32)].transpose(1,0,2)
        a, b = tile(first), tile(second)
        return display(a + (b - a) * weight)
