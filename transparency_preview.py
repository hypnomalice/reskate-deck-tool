"""CPU material preview; native game lighting remains a separate visual check."""
import numpy as np
from PIL import Image,ImageColor
from effect_preview import AtlasPreview,display
import transparency_finish as finish


def cut_field(u,v):
    """The same irregular 5 by 14 triangle field used by the approved crystal."""
    def frac(x):return x-np.floor(x)
    def hash(x,y):return frac(((x*37+y*17+5)*(x*13+y*7+11))*.0009765625)
    def node(x,y):return (x+(hash(x,y)*.44-.22)*((x>0)&(x<5)),y+(hash(x+37,y+19)*.44-.22)*((y>0)&(y<14)))
    px,py=np.broadcast_arrays(np.clip(u,0,.999999)*5,np.clip(v,0,.999999)*14);bx,by=np.floor(px),np.floor(py);sx=np.zeros_like(px);sy=np.zeros_like(py)
    def inside(a,b,c):
        return ((b[0]-a[0])*(py-a[1])-(b[1]-a[1])*(px-a[0])>=-1e-6)&((c[0]-b[0])*(py-b[1])-(c[1]-b[1])*(px-b[0])>=-1e-6)&((a[0]-c[0])*(py-c[1])-(a[1]-c[1])*(px-c[0])>=-1e-6)
    for yy in (-1,0,1):
        for xx in (-1,0,1):
            x,y=bx+xx,by+yy;a,b,c,d=node(x,y),node(x+1,y),node(x+1,y+1),node(x,y+1);alternate=frac((x+y)*.5)>.1
            first=np.where(alternate,inside(a,b,d),inside(a,b,c));second=np.where(alternate,inside(b,c,d),inside(a,c,d));hit=(x>=0)&(x<5)&(y>=0)&(y<14)&(first|second);tri=np.where(first,0,1);ix,iy=x+tri*17,y+tri*29
            sx=np.where(hit,(hash(ix+53,iy+11)*2-1)*.68,sx);sy=np.where(hit,(hash(ix+7,iy+71)*2-1)*.68,sy)
    return sx,sy


class TransparencyPreview(AtlasPreview):
    def __init__(self,atlas,mode,value=None):
        super().__init__(atlas,mode);self.optics=finish.settings(mode,value);self.clock_seconds=0.
    def set_lens_strength(self,value):pass
    def render(self,angle,size=(210,840),region=(0,0,1,1),**kwargs):
        w,h=size;u,v=np.meshgrid((np.arange(w)+.5)/w,(np.arange(h)+.5)/h);l,t,r,b=region;u=l+u*(r-l);v=t+v*(b-t)
        left,top,right,bottom=finish.ARTWORK_REGION;bu=(u-left)/(right-left);bv=(v-top)/(bottom-top);cfg=self.optics;angle=float(np.clip(angle,-1,1));sampleu,samplev=u.copy(),v.copy()
        wave=np.zeros_like(u);facet=np.zeros_like(u)
        if self.mode=='crystal':
            sx,sy=cut_field(bu,bv);sampleu+=sx*.09765;samplev+=sy*.03212895;facet=np.clip(np.abs(sx*.78+sy*.25),0,1)
        elif self.mode=='glass' and cfg['finish']=='water':
            clock=self.clock_seconds;wave=np.sin(bu*24+bv*8+clock*1.1)*.07+np.cos(bv*32-bu*7-clock*.9)*.06;sampleu+=wave*.012
        source=self.sample(np.clip(sampleu,left,right),np.clip(samplev,top,bottom)*.5)
        artwork_alpha=self.sample_alpha(np.clip(sampleu,left,right),np.clip(samplev,top,bottom)*.5)
        inset=(bu>.04)&(bu<.96)&(bv>.015)&(bv<.985)
        if self.mode=='case' and cfg['interior']=='pcb':
            x,z=(bu-.5)*.216,.415-bv*.818;inset=(np.abs(x)<.073)&(np.abs(z)<.31);source=np.zeros_like(source)+[.025,.19,.065];artwork_alpha=np.ones_like(artwork_alpha)
            traces=(np.abs(np.sin(x*950+z*11))>.97)&inset;source+=traces[...,None]*[.06,.075,.025]
            for cx,cz,hx,hz in [(-.025,.22,.022,.035),(.025,.075,.024,.040),(-.020,-.12,.025,.038),(.025,-.235,.017,.023)]:
                chip=(np.abs(x-cx)<hx)&(np.abs(z-cz)<hz);source=np.where(chip[...,None],[.045,.05,.055],source)
        if self.mode=='glass' and cfg['finish']=='liquid':
            label_alpha=artwork_alpha*inset
            x,z=(bu-.5)*.216,.415-bv*.818
            radius=.108-cfg['rim_mm']*.001
            end_distance=np.maximum(np.abs(z-.006)-.301,0)
            inset=x*x+end_distance*end_distance<radius*radius
            wet=(z+x*np.sin(angle)<0)&inset
            liquid_colour=(np.array(ImageColor.getrgb(cfg['liquid_colour']))/255.)**2.2
            base=np.where(wet[...,None],liquid_colour*.21,[.10,.15,.17])
            base_alpha=np.where(wet,.05+.88*cfg['opacity'],.05)
            alpha=label_alpha+base_alpha*(1-label_alpha)
            rgb=(source*label_alpha[...,None]+base*(base_alpha*(1-label_alpha))[...,None])/alpha[...,None]
            rgba=display(rgb).convert('RGBA')
            rgba.putalpha(Image.fromarray(np.uint8(np.rint(255*alpha))))
            return rgba
        haze=0 if self.mode=='case' and cfg['finish']=='glossy' else cfg['haze'];tint=(np.array(ImageColor.getrgb(cfg['tint']))/255.)**2.2
        rough=cfg['roughness'];width=.035+rough*.18;highlight=np.exp(-((bu-(.35+angle*.45+wave*.8))/(width))**2)*(.12+.32*abs(angle));highlight*=cfg['reflection_strength']
        reflection=np.stack((highlight*.93,highlight*.98,highlight),axis=-1);source=source*(.72+.28*(1-facet[...,None]))
        rgb=source*(1-haze*.4)+tint*haze*.25+reflection;rgb=rgb*(1-cfg['tint_strength']*.12)+tint*cfg['tint_strength']*.06
        edge=np.clip((np.abs(bu-.5)-.40)/.1,0,1);coverage=np.clip(.04+.5*abs(angle)**5+edge*.45+haze*.25+facet*.16,0,1)
        shell=tint*.10+reflection+edge[...,None]*[.025,.08,.07]
        art_alpha=np.where(inset,artwork_alpha,0)
        alpha=art_alpha+coverage*(1-art_alpha)
        rgb=(rgb*art_alpha[...,None]+shell*(coverage*(1-art_alpha))[...,None])/np.maximum(alpha[...,None],1e-6)
        rgba=display(rgb).convert('RGBA');rgba.putalpha(Image.fromarray(np.uint8(np.rint(alpha*255))))
        return rgba
