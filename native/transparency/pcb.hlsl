// Existing native material values: no new buffer, texture or root binding.
cbuffer TransparencyMaterial : register(b1) { float4 OpticalMaterial[5]; };
bool opticalAuthoring() { return abs(OpticalMaterial[3].z-.917)<.00005; }
float opticalStrength(float fallback) { return opticalAuthoring()?saturate(OpticalMaterial[1].x):fallback; }
float opticalHaze(float fallback) { return opticalAuthoring()?saturate(OpticalMaterial[1].y):fallback; }
float opticalRoughness(float fallback) { return opticalAuthoring()?clamp(OpticalMaterial[1].z,0,1):fallback; }
float opticalReflection() { return opticalAuthoring()?clamp(OpticalMaterial[2].x*2,0,2):1; }
float opticalThickness() { return opticalAuthoring()?clamp(OpticalMaterial[2].y*.03,.001,.03):.010; }
float3 opticalTint(float3 fallback) { return opticalAuthoring()?pow(saturate(OpticalMaterial[0].xyz),2.2):fallback; }
float2 opticalCutGrid() {
 float amount=opticalAuthoring()?clamp(OpticalMaterial[3].y*400,12,400):140;
 float columns=max(2,round(sqrt(amount*5./28.)));
 return float2(columns,max(2,round(amount/(2*columns))));
}

// Studio-reflection fallback. No sampled textures, scene captures, or new buffers.
// This is not a reconstruction of the game's real environment lighting.
cbuffer BoardPass : register(b4) { float4 Board[488]; };
struct Fragment { float4 world:TEXCOORD0; float4 b:TEXCOORD1; float4 c:TEXCOORD2; float4 d:TEXCOORD3; float4 screen:SV_Position; };
float rectangle(float2 p,float2 centre,float2 halfSize,float softness) {
 softness*=1+opticalRoughness(0)*4;
 float2 q=abs(p-centre)-halfSize;
 return 1-smoothstep(0,softness,max(q.x,q.y));
}
float3 studio(float3 direction,float3 eye) {
 float3 up=abs(eye.y)>.98 ? float3(0,0,1) : float3(0,1,0);
 float3 right=normalize(cross(up,eye));up=cross(eye,right);
 float3 r=float3(dot(direction,right),dot(direction,up),dot(direction,eye));
 float3 radiance=lerp(float3(.14,.16,.19),float3(.85,.92,1.05),smoothstep(-.7,.8,r.y));
 float2 p=r.xy/max(r.z,.05);
 float visible=smoothstep(.04,.16,r.z);
 float window=rectangle(p,float2(-.48,.18),float2(.22,.85),.24);
 float card=rectangle(p,float2(.62,-.12),float2(.35,.45),.30);
 float top=rectangle(p,float2(.02,.72),float2(.65,.055),.06);
 radiance+=visible*(window*float3(9,8.7,8.2)+card*float3(3.3,3.6,4.1)+top*float3(2,2,2));
 return radiance;
}
static const float2 mountCentres[8]={float2(-0.021600000,0.244856000),float2(-0.021600000,0.190868000),float2(0.021600000,0.244856000),float2(0.021600000,0.190868000),float2(-0.021600000,-0.192774000),float2(-0.021600000,-0.246762000),float2(0.021600000,-0.192774000),float2(0.021600000,-0.246762000)};
static const float2 caseCentres[4]={float2(-0.082080000,0.337290000),float2(0.082080000,0.337290000),float2(-0.082080000,-0.325290000),float2(0.082080000,-0.325290000)};
float mountingDistance(float2 p) {
 float result=100;
 [unroll]for(int j=0;j<8;j++)result=min(result,length(p-mountCentres[j]));
 return result;
}
float3 grainGradient(float2 p){
 float2 cell=floor(p),f=frac(p);f=f*f*(3-2*f);
 float4 ids=float4(dot(cell,float2(127.1,311.7)),dot(cell+float2(1,0),float2(127.1,311.7)),dot(cell+float2(0,1),float2(127.1,311.7)),dot(cell+1,float2(127.1,311.7)));
 float4 h=frac(sin(ids)*43758.5453);
 float2 raw=frac(p),d=6*raw*(1-raw);
 return float3(lerp(lerp(h.x,h.y,f.x),lerp(h.z,h.w,f.x),f.y),lerp(h.y-h.x,h.w-h.z,f.y)*d.x,lerp(h.z-h.x,h.w-h.y,f.x)*d.y);
}
float rectangleCoverage(float2 p,float2 centre,float2 halfSize,float width) {
 float2 d=abs(p-centre)-halfSize;return 1-smoothstep(-width,width,max(d.x,d.y));
}
float traceSegment(float2 p,float2 a,float2 b){
 float2 d=b-a;float t=saturate(dot(p-a,d)/max(dot(d,d),1e-10));
 return length(p-(a+d*t));
}
float routedTraces(float2 p){
 static const float4 first[8]={float4(-.003,.21,.055,.21),float4(-.003,.23,.063,.23),float4(-.047,.20,-.061,.20),float4(.001,.065,-.010,.065),float4(.005,-.13,.052,-.13),float4(.008,-.24,-.056,-.24),float4(.020,.285,.060,.285),float4(-.052,-.285,.018,-.285)};
 static const float4 last[8]={float4(.055,.09,.049,.09),float4(.063,.06,.049,.06),float4(-.061,-.11,-.045,-.11),float4(-.010,-.08,-.020,-.082),float4(.052,-.22,.042,-.22),float4(-.056,-.14,-.045,-.14),float4(.060,.245,.040,.245),float4(.018,-.26,.025,-.258)};
 float distance=100;
 [unroll]for(int n=0;n<8;n++){
  distance=min(distance,traceSegment(p,first[n].xy,first[n].zw));
  distance=min(distance,traceSegment(p,first[n].zw,last[n].xy));
  distance=min(distance,traceSegment(p,last[n].xy,last[n].zw));
 }
 return 1-smoothstep(.00035,.00085,distance);
}
float4 chipBox(float2 surface,float2 shift,float4 chip,float nearDepth,float farDepth){
 float3 origin=float3(surface.x,0,surface.y);
 float3 direction=float3(shift.x,1,shift.y);
 float3 safe=float3(abs(direction.x)<1e-5?(direction.x<0?-1e-5:1e-5):direction.x,1,abs(direction.z)<1e-5?(direction.z<0?-1e-5:1e-5):direction.z);
 float3 centre=float3(chip.x,(nearDepth+farDepth)*.5,chip.y),halfSize=float3(chip.z,(farDepth-nearDepth)*.5,chip.w);
 float3 a=(centre-halfSize-origin)/safe,b=(centre+halfSize-origin)/safe;
 float3 enter=min(a,b),leave=max(a,b);
 float t=max(enter.x,max(enter.y,enter.z)),end=min(leave.x,min(leave.y,leave.z));
 float coverage=(1-smoothstep(-.00015,.00015,t-end))*step(0,end);
 float3 n=enter.x>=enter.y&&enter.x>=enter.z?float3(-sign(safe.x),0,0):(enter.y>=enter.z?float3(0,-1,0):float3(0,0,-sign(safe.z)));
 float3 hit=origin+direction*max(t,0)-centre;
 float bevel=(1-smoothstep(.0003,.0011,min(chip.z-abs(hit.x),chip.w-abs(hit.z))))*abs(n.y);
 float light=.32+.68*saturate(dot(n,normalize(float3(-.45,-.85,-.25))));
 float marking=1-smoothstep(.0011,.0018,length(hit.xz-float2(-chip.z+.005,-chip.w+.005)));
 float3 colour=float3(.038,.044,.049)*light+bevel*.014+marking*.012*abs(n.y);
 return float4(colour,coverage);
}
float4 pcb(float2 uv,float2 shift,float2 cone,float planeRadius,float chipRadius,float planeDepth,float chipDepth,bool chipSide) {
 float2 p=float2((uv.x-.5)*.216,.415-uv.y*.818);
 float2 platePoint=p+shift*planeDepth+cone*planeRadius;
 float plate=rectangleCoverage(platePoint,0,float2(.073,.31),.0005);
 plate*=smoothstep(.0036,.0045,mountingDistance(platePoint));
 [branch]if(plate<.0001)return 0;
 p=platePoint;
 float trace=routedTraces(p);
 float3 c=float3(.023,.16,.054)+trace*float3(.035,.08,.025);
 static const float4 chips[4]={float4(-.025,.22,.022,.035),float4(.025,.075,.024,.040),float4(-.020,-.12,.025,.038),float4(.025,-.235,.017,.023)};
 [branch]if(chipSide){
 [unroll]for(int j=0;j<4;j++){
  float2 origin=float2((uv.x-.5)*.216,.415-uv.y*.818)+cone*chipRadius;
  float4 box=chipBox(origin,shift,chips[j],chipDepth,max(chipDepth+.0004,planeDepth-.0002));
  float2 pinPoint=origin+shift*((chipDepth+planeDepth)*.5);
  float pinRow=rectangleCoverage(pinPoint,chips[j].xy,chips[j].zw+float2(.007,-.003),.0005)*(chipSide?1:0);
  float teeth=1-smoothstep(.001,.002,abs(frac((pinPoint.y-chips[j].y)/(chips[j].w*.4))-.5)*chips[j].w*.4);
  float shadow=rectangleCoverage(platePoint,chips[j].xy+float2(.002,-.002),chips[j].zw+float2(.001,.001),.002)*(chipSide?1:0);
  c*=1-shadow*.20;
  c=lerp(c,float3(.32,.29,.17),pinRow*teeth);
  c=lerp(c,box.rgb,box.a*(chipSide?1:0));
 }
 }
 return float4(c*plate,plate);
}
float4 main(Fragment i):SV_Target0 {
 float3 eye=Board[455].xyz-i.world.xyz,normal=i.d.xyz;
 float vl=dot(eye,eye),nl=dot(normal,normal);
 if(vl<1e-12 || nl<1e-18)return 0;
 eye*=rsqrt(vl);normal*=rsqrt(nl);
 float2 uv=float2(i.d.w*2,i.c.w);
 float3 px=ddx(i.world.xyz),py=ddy(i.world.xyz);
 float2 ux=ddx(uv),uy=ddy(uv);float det=ux.x*uy.y-uy.x*ux.y;
 float handed=det<0?-1:1;
 float3 fallback=i.b.xyz-normal*dot(i.b.xyz,normal);
 float3 rawT=abs(det)>1e-12?(px*uy.y-py*ux.y)*handed:fallback;
 rawT-=normal*dot(rawT,normal);
 float3 tangent=rawT*rsqrt(max(dot(rawT,rawT),1e-18));
 float3 bitangent=cross(normal,tangent);
 float3 rawB=(py*ux.x-px*uy.x)*handed;
 if(abs(det)>1e-12 && dot(rawB,bitangent)<0)bitangent=-bitangent;
 bool chipSide=dot(normal,cross(tangent,bitangent))<0;
 bool outsideFace=dot(normal,eye)>0;
 if(dot(normal,eye)<0)normal=-normal;
 float facing=saturate(dot(normal,eye));
 float fresnel=.039+.961*pow(1-facing,5);
 float2 density=float2(260,1000);
 float footprint=max(length(ddx(uv)*density),length(ddy(uv)*density));
 float attenuation=1-smoothstep(.5,2,footprint);
 float3 micro=grainGradient(uv*density);
 float3 roughNormal=normalize(normal+(tangent*micro.y+bitangent*micro.z)*(.12*attenuation*opticalRoughness(.48)/.48));
 float3 reflection=studio(reflect(-eye,roughNormal),eye)*.28;
 float2 view=float2(dot(eye,tangent),dot(eye,bitangent))/max(abs(dot(eye,normal)),.18);
 // Hollow wall and air gap are distinct. Only polymer attenuates light.
 float edge=saturate(i.world.w);
 float2 localP=float2((uv.x-.5)*.216,.415-uv.y*.818);
 float bossBand=1-smoothstep(.0065,.010,mountingDistance(localP));
 float caseBand=0;
 [unroll]for(int n=0;n<4;n++)caseBand=max(caseBand,1-smoothstep(.005,.009,length(localP-caseCentres[n])));
 float wallRim=max(edge,smoothstep(.084,.104,abs(localP.x)));
 float wall=(.0009+wallRim*.0028+max(bossBand,caseBand)*.0018)*opticalThickness()/.010;
 float eta=1/1.49;
 float insideCos=sqrt(max(1-eta*eta*(1-facing*facing),.0001));
 float polymerPath=wall/insideCos;
 float3 transmittance=exp(-float3(18,9,5)*polymerPath);
 float planeDepth=chipSide?.005:.002;
 float chipDepth=chipSide?.002:.005;
 float planeGap=max(planeDepth-wall,0);
 float chipGap=max(chipDepth-wall,0);
 // The fixed cone footprint grows with distance behind the rough wall.
 float planeRadius=clamp((wall*.30+planeGap*.65)*opticalHaze(.42)/.42,0,.006);
 float chipRadius=clamp((wall*.30+chipGap*.65)*opticalHaze(.42)/.42,0,.006);
 static const float2 taps[8]={float2(-.326,-.406),float2(-.84,-.074),float2(-.696,.457),float2(-.203,.621),float2(.962,-.195),float2(.473,-.48),float2(.519,.767),float2(.185,-.893)};
 float4 interior=0;
 [unroll]for(int k=0;k<8;k++)interior+=pcb(uv,float2(-view.x,view.y),taps[k],planeRadius,chipRadius,planeDepth,chipDepth,chipSide);
 interior*=outsideFace?.125:0;
 float scatter=(1-(1-.02)*exp(-90*polymerPath))*opticalHaze(.42)/.42;
 float grain=(micro.x-.5)*attenuation;
 float3 milk=lerp(float3(.48,.52,.53),opticalTint(float3(.48,.52,.53)),opticalStrength(0))+grain*.045;
 reflection*=(1+grain*.18)*opticalReflection();
 float pcbAlpha=interior.a*.92;
 float3 filtered=interior.rgb*.92*transmittance;
 float alpha=1-(1-pcbAlpha)*(1-scatter)*(1-fresnel);
 float3 colour=filtered*(1-scatter)+milk*scatter+reflection*fresnel;
 // Shaded bores retain the old case treatment; native geometry is not drilled.
 float2 p=float2((uv.x-.5)*.216,.415-uv.y*.818);
 float2 rayShift=float2(-view.x,view.y);
 float r=mountingDistance(p);
 float aa=clamp(max(length(ddx(p)),length(ddy(p)))*.7,.0001,.001);
 float boss=(1-smoothstep(.0065-aa,.0065+aa,r))*(outsideFace?1:0);
 float mouth=1-smoothstep(.0033-aa,.0033+aa,r);
 float throat=1-smoothstep(.0028-aa,.0028+aa,mountingDistance(p+rayShift*.0045));
 float rim=(1-smoothstep(.0004,.0010,abs(r-.0052)))*boss;
 float3 bossColour=float3(.25,.29,.30)+rim*.12;
 float3 boreColour=lerp(float3(.12,.17,.18),float3(.022,.028,.03),throat);
 float3 mountingColour=lerp(bossColour,boreColour,mouth);
 colour=lerp(colour,mountingColour,boss*.92);alpha=lerp(alpha,1,boss*.92);
 // Four case assembly recesses, distinct from the eight native truck mounts.
 [unroll]for(int j=0;j<4;j++){
  float2 q=p-caseCentres[j];float radius=length(q);
  float recess=(1-smoothstep(.0058-aa,.0058+aa,radius))*(outsideFace?1:0);
  float lip=1-smoothstep(.00035,.0009,abs(radius-.0048));
  float bore=1-smoothstep(.0022-aa,.0022+aa,length(q+rayShift*.003));
  float3 assembly=lerp(float3(.19,.24,.25)+lip*.14,float3(.025,.033,.035),bore);
  colour=lerp(colour,assembly,recess*.94);alpha=lerp(alpha,1,recess*.94);
 }
 return float4(colour,saturate(alpha));
}
