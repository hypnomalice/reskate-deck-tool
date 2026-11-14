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
 float window=rectangle(p,float2(-.48,.18),float2(.11,.85),.055);
 float card=rectangle(p,float2(.62,-.12),float2(.23,.36),.10);
 float top=rectangle(p,float2(.02,.72),float2(.65,.055),.06);
 radiance+=visible*(window*float3(9,8.7,8.2)+card*float3(3.3,3.6,4.1)+top*float3(2,2,2));
 return radiance;
}
float4 main(Fragment i):SV_Target0 {
 float3 eye=Board[455].xyz-i.world.xyz,normal=i.d.xyz;
 float vl=dot(eye,eye),nl=dot(normal,normal);
 if(vl<1e-12 || nl<1e-18)return 0;
 eye*=rsqrt(vl);normal*=rsqrt(nl);
 float3 tangent=i.b.xyz-normal*dot(i.b.xyz,normal);
 float tangentLength=dot(tangent,tangent);
 if(tangentLength>1e-12){
  tangent*=rsqrt(tangentLength);
  float3 bitangent=normalize(cross(normal,tangent));
  float2 uv=float2(i.d.w*2,i.c.w);
  float time=Board[452].x;
  float2 slope=float2(cos(uv.x*24+uv.y*8+time*1.1)*.07+cos(uv.x*11-uv.y*17-time*.7)*.035,
                      sin(uv.y*32-uv.x*7-time*.9)*.06+sin(uv.y*13+uv.x*19+time*.6)*.025);
  normal=normalize(normal+tangent*slope.x+bitangent*slope.y);
 }
 if(dot(normal,eye)<0)normal=-normal;
 float facing=saturate(dot(normal,eye));
 float fresnel=.0204+.9796*pow(1-facing,5);
 float3 reflection=studio(reflect(-eye,normal),eye);
 // Neutral absorption estimate for the existing ~10mm shell. Scalar blending
 // cannot reproduce wavelength-dependent absorption without reading the scene.
 float path=opticalThickness()/max(facing,.06);
 float absorbed=1-exp2(-.25*path*1.442695);
 float coverage=saturate(fresnel+(1-fresnel)*absorbed);
 float edge=saturate(i.world.w);
 float edgeCoverage=edge*.50;
 float3 edgeScatter=float3(.035,.13,.17)*edgeCoverage;
 float haze=opticalHaze(0)*.6;
 float strength=opticalStrength(0);
 float tintCoverage=strength*(1-exp(-path*18));
 float total=1-(1-coverage)*(1-edgeCoverage)*(1-haze)*(1-tintCoverage);
 float3 tint=opticalTint(float3(1,1,1));
 float3 colour=reflection*fresnel*opticalReflection()+edgeScatter+tint*(haze*.4+tintCoverage*.24);
 return float4(colour,saturate(total));
}
