// Ported unchanged from findastra/astras-infinite-pole (theatre branch, Assets/Astra/Shaders/GlitterCloud.shader) for the House's Stormscape.
Shader "Astra/Glitter Cloud" {
 // 2026-10-01 (Claude): Stormscape turns every cloud into a dark rainbow gradient of greys and blacks (AstraStorm.cginc).
 // Claude round 3a/3f: soft, rounded cloud shading with twinkling glitter.
 // Every cloud gets its own pastel tint (close to white) that slowly shifts as it drifts and over time.
 // Instanced, no textures. The DJ deck uses this shader too, with Color variety set to 0.
 Properties {
  _Top("Top color",Color)=(1,.97,1,1)
  _Bottom("Underside color",Color)=(.93,.84,.95,1)
  _Rim("Rim glow",Color)=(1.5,1.2,1.6,1)
  _Glitter("Glitter",Range(0,4))=2.2
  _Pastel("Color variety (0 = none)",Range(0,1))=.2
  _ColorSpeed("Color change speed",Range(0,.2))=.025
 }
 SubShader {Tags {"Queue"="Geometry" "RenderType"="Opaque"}
 Pass {CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #pragma multi_compile_instancing
 #include "UnityCG.cginc"
 #include "AstraStorm.cginc"
 struct appdata {float4 vertex:POSITION;float3 normal:NORMAL;UNITY_VERTEX_INPUT_INSTANCE_ID};
 struct v2f {float4 pos:SV_POSITION;float3 world:TEXCOORD0;float3 normal:TEXCOORD1;float3 center:TEXCOORD2;UNITY_VERTEX_OUTPUT_STEREO};
 float4 _Top,_Bottom,_Rim;float _Glitter,_Pastel,_ColorSpeed;
 float Hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float Hash3(float3 p){return frac(sin(dot(p,float3(127.1,311.7,74.7)))*43758.5453);}
 // 2026-09-26 (Claude): glints live in 3D cells, so every sparkle is a round point on any surface angle (no stretching).
 float Glints(float3 p,float speed,float density){
  float3 cell=floor(p);float h=Hash3(cell);float3 f=frac(p)-.5;
  float3 off=float3(Hash3(cell+3.1),Hash3(cell+7.7),Hash3(cell+5.3))-.5;
  float spot=pow(saturate(1-length(f-off*.6)*2.6),4);
  float flash=pow(saturate(.5+.5*sin(_Time.y*speed+h*63)),10);
  return spot*flash*step(1-density,h)*saturate(1-length(fwidth(p))*.35);
 }
 v2f vert(appdata v){v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
  o.pos=UnityObjectToClipPos(v.vertex);o.world=mul(unity_ObjectToWorld,v.vertex).xyz;o.normal=UnityObjectToWorldNormal(v.normal);
  o.center=mul(unity_ObjectToWorld,float4(0,0,0,1)).xyz;return o;}
 half4 frag(v2f i):SV_Target{UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
  float3 n=normalize(i.normal);float3 eye=normalize(_WorldSpaceCameraPos-i.world);
  // pastel tint: differs per cloud (from where it is), drifts as the cloud moves and over time, plus a soft gradient across the cloud
  float hue=dot(i.center,float3(.047,.031,.061))+_Time.y*_ColorSpeed+dot(i.world-i.center,float3(.06,.09,.05));
  float3 rainbow=.5+.5*cos(6.2832*(hue+float3(0,.33,.67)));
  float3 tint=lerp(float3(1,1,1),rainbow,_Pastel);
  // soft, rounded shading: bright tops, gently shaded sides and underside
  float up=saturate(n.y*.55+.5);
  float3 col=tint*lerp(_Bottom.rgb,_Top.rgb,up)*(.86+.14*up);
  float rim=pow(1-saturate(dot(n,eye)),2.2);
  float3 p=i.world;
  float g=Glints(p*90,1.7,.5)+Glints(p*34+11.3,1.1,.35)*1.4;
  float3 calm=col+_Rim.rgb*tint*rim*.45+float3(1,.95,1)*g*_Glitter*2;
  if(_UdonStorm<=0)return half4(calm,1);
  float3 storm=StormCloud(i.world,i.center,up,rim)+float3(.75,.8,1)*g*_Glitter*.18;   // glitter becomes faint wet glints
  return half4(lerp(calm,storm,_UdonStorm),1);
 }
 ENDCG }
 }
}
