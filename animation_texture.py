from pathlib import Path
import math
import re
import struct
import sys

from PIL import Image, ImageDraw

import animation

WIDTH, HEIGHT = 512, 4096
FIELDS = ('duration', 'count', 'columns', 'cell_w', 'cell_h', 'frame_w', 'frame_h',
          'board_x', 'board_y', 'board_w', 'board_h', 'brightness', 'tick_rate')


def srgb(value):
    return round(255*(12.92*value if value <= .0031308 else 1.055*value**(1/2.4)-.055))


def word(value):
    value = int(value)
    if not 0 <= value <= 4095:
        raise ValueError('Animation metadata exceeds the supported range.')
    return tuple(srgb((value >> shift & 15)/15) for shift in (0,4,8))


def read_word(colour):
    result = 0
    for shift, channel in zip((0,4,8), colour[:3]):
        c = channel/255
        linear = c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4
        result |= round(linear*15) << shift
    return result


def atlas(clip, brightness=2, background="#ffffff", placement=None, quality=1):
    if quality not in (1,2,4):
        raise ValueError('Animation quality must be 1, 2 or 4.')
    if not 1 <= len(clip.frames) <= 512:
        raise ValueError('Animated decks support 1–512 frames.')
    if clip.duration_ms > 40950:
        raise ValueError('Animated decks support clips up to 40.95 seconds.')
    original = clip.frames[0]
    # Crop once in board space so placement also works at the deck edges.
    settings = placement or {}
    zoom = float(settings.get('zoom', 1))
    ox, oy = (float(settings.get(axis, 0)) for axis in ('x','y'))
    if not all(math.isfinite(v) for v in (zoom,ox,oy,brightness)) or not .1 <= zoom <= 5 or max(abs(ox),abs(oy)) > 1 or not .1 <= brightness <= 4:
        raise ValueError('Invalid animation placement or brightness.')
    scale = min(1,512/original.width,2048/original.height)*zoom
    full_w, full_h = (max(1,round(v*scale)) for v in original.size)
    left, top = round((512-full_w)/2+ox*512), round((2048-full_h)/2+oy*2048)
    x0,y0,x1,y1=max(0,left),max(0,top),min(512,left+full_w),min(2048,top+full_h)
    if x1<=x0 or y1<=y0:
        raise ValueError('The animation is entirely outside the board.')
    board_w,board_h=x1-x0,y1-y0
    storage_scale=min(1,252/board_w)
    while True:
        w,h=max(1,round(board_w*storage_scale)),max(1,round(board_h*storage_scale))
        columns=512//(w+4)
        if 256+math.ceil(len(clip.frames)/columns)*(h+4)<=4096:
            break
        storage_scale*=.95
    tick_rate=1000 if clip.duration_ms<=4095 else 100
    ticks = [max(1,round(end*tick_rate/1000)) for end in clip.ends_ms]
    values = dict(duration=ticks[-1], count=len(clip.frames), columns=columns,
                  cell_w=w+4,cell_h=h+4,frame_w=w,frame_h=h,
                  board_x=x0,board_y=y0,
                  board_w=board_w,board_h=board_h,brightness=round(brightness*100),tick_rate=tick_rate)
    out = Image.new('RGB',(512,4096),background)
    d = ImageDraw.Draw(out)
    for i,c in enumerate(((255,0,255),(0,255,255),(255,255,0),(0,255,0))):
        d.rectangle((i*128,0,i*128+127,63),fill=c)
    d.rectangle((0,48,127,63),fill=(188,255,0))
    for i,name in enumerate(FIELDS):
        d.rectangle((i*32,64,i*32+31,127),fill=word(values[name]))
    for i in range(512):
        x,y=i%128*4,128+i//128*16
        d.rectangle((x,y,x+3,y+15),fill=word(ticks[min(i,len(ticks)-1)]))
    if quality!=1:
        out=out.resize((512*quality,4096*quality),Image.Resampling.NEAREST)
    stored_w,stored_h=w*quality,h*quality
    for i,frame in enumerate(clip.frames):
        canvas = Image.new('RGBA',frame.size,background)
        canvas.alpha_composite(frame.convert('RGBA'))
        crop=((x0-left)*original.width/full_w,(y0-top)*original.height/full_h,
              (x1-left)*original.width/full_w,(y1-top)*original.height/full_h)
        frame=canvas.convert('RGB').resize((stored_w,stored_h),Image.Resampling.LANCZOS,box=crop)
        pad=2*quality
        padded=Image.new('RGB',(stored_w+2*pad,stored_h+2*pad))
        padded.paste(frame,(pad,pad))
        for dx,dy,box in ((0,pad,(0,0,1,stored_h)),(pad+stored_w,pad,(stored_w-1,0,stored_w,stored_h)),(pad,0,(0,0,stored_w,1)),(pad,pad+stored_h,(0,stored_h-1,stored_w,stored_h))):
            piece=frame.crop(box)
            padded.paste(piece.resize((pad if piece.width==1 else stored_w,pad if piece.height==1 else stored_h)),(dx,dy))
        for dx,dy,px,py in ((0,0,0,0),(pad+stored_w,0,stored_w-1,0),(0,pad+stored_h,0,stored_h-1),(pad+stored_w,pad+stored_h,stored_w-1,stored_h-1)):
            padded.paste(frame.getpixel((px,py)),(dx,dy,dx+pad,dy+pad))
        out.paste(padded,(i%columns*(w+4)*quality,(256+i//columns*(h+4))*quality))
    return out,dict(values,ticks=ticks,source_size=original.size,storage_size=(stored_w,stored_h),atlas_size=out.size)



def preview_frame(clip, index, background, placement):
    frame = clip.frames[index].convert('RGBA')
    channels = frame.split()
    lut=[]
    for n in range(256):
        value=n/255
        linear=value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4
        lut.append(srgb(2*linear/(1+linear)))
    lifted=Image.merge('RGBA',tuple(c.point(lut) for c in channels[:3])+(channels[3],))
    one=animation.Animation((lifted,),(100,),0)
    return one.board_frame(0,background=background,placement=placement)
