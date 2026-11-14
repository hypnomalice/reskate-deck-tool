#include <cmath>
#include <algorithm>
#include <thread>
// CPU implementation of the exported inverse warp. No simulation or gain changes.
static double smooth(double t) { t=std::clamp(t,0.,1.);return t*t*(3-2*t); }
extern "C" __declspec(dllexport) void render_springs(const float* p,int aw,int ah,unsigned char* out,int w,int h,const double* c) {
 auto sample=[&](double u,double v,int channel) {
  double x=std::clamp(u*aw-.5,0.,double(aw-1)),y=std::clamp(v*ah-.5,0.,double(ah-1));
  int x0=int(x),y0=int(y),x1=std::min(x0+1,aw-1),y1=std::min(y0+1,ah-1);double a=x-x0,b=y-y0;
  return (p[(y0*aw+x0)*3+channel]*(1-a)+p[(y0*aw+x1)*3+channel]*a)*(1-b)+(p[(y1*aw+x0)*3+channel]*(1-a)+p[(y1*aw+x1)*3+channel]*a)*b;
 };
 double tx=sample(.125,36./4096,0)*512,ty=sample(.125,36./4096,1)*2048;
 double radius=std::max(sample(.125,36./4096,2)*512,1.);
 double bx=sample(.375,36./4096,0)*512,by=sample(.375,36./4096,1)*2048,split=sample(.375,36./4096,2)*512;
 double ax=bx-tx,ay=by-ty,length=std::max(std::hypot(ax,ay),1.);ax/=length;ay/=length;double centre_y=(ty+by)*.5;
 auto rows=[&](int start,int end){for(int j=start;j<end;++j)for(int i=0;i<w;++i){
  double u=c[0]+(i+.5)/w*(c[2]-c[0]),v=c[1]+(j+.5)/h*(c[3]-c[1]);
  double px=u*512,py=v*2048,x=px,y=py;
  for(int k=0;k<8;++k){
   double mask=sample(x/512,.5+y/4096,0)*smooth(std::hypot(x-tx,y-ty)/radius)*smooth(((x-tx)*ax+(y-ty)*ay)/70);
   if(c[8]>0)mask*=smooth(std::hypot(x-bx,y-by)/radius)*smooth(((bx-x)*ax+(by-y)*ay)/60);
   double b=smooth(((x-split)*ay-(y-centre_y)*ax+20)/40);
   double dx=mask*(c[4]+b*(c[6]-c[4]))*32,dy=mask*(c[5]+b*(c[7]-c[5]))*32;
   x+=(px-(x+dx))*.7;y+=(py-(y+dy))*.7;
  }
  u=x/512;v=y/2048;double source=u;
  for(int k=0;k<6;++k)source=(source+u+sample(source,.5+v*.5,1)*c[9])*.5;
  for(int ch=0;ch<3;++ch){double a=std::clamp(sample(source,64./4096+v*1984./4096,ch),0.,1.);a=a<=.0031308?a*12.92:1.055*std::pow(a,1/2.4)-.055;out[(j*w+i)*3+ch]=(unsigned char)std::nearbyint(a*255);}
 }
 };
 std::thread a(rows,0,h/4),b(rows,h/4,h/2),d(rows,h/2,h*3/4);rows(h*3/4,h);a.join();b.join();d.join();
}

extern "C" __declspec(dllexport) void render_layered_springs(const float* p,int aw,int ah,unsigned char* out,int w,int h,const double* c) {
 auto sample=[&](int page,double u,double v,int channel) {
  double x=std::clamp(u*aw-.5,0.,double(aw-1)),y=std::clamp(v*ah-.5,0.,double(ah-1));
  int x0=int(x),y0=int(y),x1=std::min(x0+1,aw-1),y1=std::min(y0+1,ah-1);double a=x-x0,b=y-y0;const float* data=p+page*aw*ah*3;
  return (data[(y0*aw+x0)*3+channel]*(1-a)+data[(y0*aw+x1)*3+channel]*a)*(1-b)+(data[(y1*aw+x0)*3+channel]*(1-a)+data[(y1*aw+x1)*3+channel]*a)*b;
 };
 double tx=sample(0,.125,36./4096,0)*512,ty=sample(0,.125,36./4096,1)*2048,radius=std::max(sample(0,.125,36./4096,2)*512,1.);
 double bx=sample(0,.375,36./4096,0)*512,by=sample(0,.375,36./4096,1)*2048,split=sample(0,.375,36./4096,2)*512;
 double ax=bx-tx,ay=by-ty,length=std::max(std::hypot(ax,ay),1.);ax/=length;ay/=length;double centre_y=(ty+by)*.5;
 auto rows=[&](int start,int end){for(int j=start;j<end;++j)for(int i=0;i<w;++i){
  double u=c[0]+(i+.5)/w*(c[2]-c[0]),v=c[1]+(j+.5)/h*(c[3]-c[1]),px=u*512,py=v*2048,x=px,y=py;
  for(int k=0;k<8;++k){
   double mask=sample(0,x/512,.5+y/4096,0)*smooth(std::hypot(x-tx,y-ty)/radius)*smooth(((x-tx)*ax+(y-ty)*ay)/70);
   if(c[8]>0)mask*=smooth(std::hypot(x-bx,y-by)/radius)*smooth(((bx-x)*ax+(by-y)*ay)/60);
   double b=smooth(((x-split)*ay-(y-centre_y)*ax+20)/40),dx=mask*(c[4]+b*(c[6]-c[4]))*32,dy=mask*(c[5]+b*(c[7]-c[5]))*32;
   double height=sample(0,x/512,.5+y/4096,1);x+=(px-(x+dx-height*c[9]*512))*.7;y+=(py-(y+dy))*.7;
  }
  double mu=x/512,mv=y/2048,bu=u,fu=u;
  for(int k=0;k<6;++k){bu=(bu+u+sample(1,bu,.5+v*.5,0)*c[9])*.5;fu=(fu+u+sample(0,fu,.5+v*.5,2)*c[9])*.5;}
  double alpha=(mu>=0&&mu<=1&&mv>=0&&mv<=1)?sample(1,mu,.5+mv*.5,1):0;
  if(sample(1,.125,36./4096,0)<.5)alpha*=1-sample(1,mu,.5+mv*.5,2);
  double front=(fu>=0&&fu<=1)?sample(1,fu,.5+v*.5,2):0;
  auto colour=[&](int page,double cu,double cv,int ch){return sample(page,std::clamp(cu,.5/512,1-.5/512),64./4096+std::clamp(cv,.5/2048,1-.5/2048)*1984./4096,ch);};
  for(int ch=0;ch<3;++ch){double bg=colour(1,bu,v,ch),move=colour(0,mu,mv,ch),fg=colour(2,fu,v,ch);double a=bg+(move-bg)*alpha;a=std::clamp(a+(fg-a)*front,0.,1.);a=a<=.0031308?a*12.92:1.055*std::pow(a,1/2.4)-.055;out[(j*w+i)*3+ch]=(unsigned char)std::nearbyint(a*255);}
 }};
 std::thread a(rows,0,h/4),b(rows,h/4,h/2),d(rows,h/2,h*3/4);rows(h*3/4,h);a.join();b.join();d.join();
}
