// Ported unchanged from findastra/astras-infinite-pole (theatre branch, Assets/Astra/Shaders/PrismaticStair.shader) for the House's Stormscape.
Shader "Astra/Prismatic Stair" {
 // Claude round 1: no edge lines, dense pink glitter, hue slider (_Hue 0 = pink).
 // Round 3b: rainbow gradients that drift with height (so falling runs through the rainbow) + brighter HDR sparkles for bloom.
 // 2026-09-24 (Claude): owner asked for 5x longer color transitions: height rates /5, per-turn swirl amplitude /5.
 Properties {
  _Color("Base color",Color)=(1,.42,.74,1)
  _Hue("Hue shift",Range(0,1))=0
  _Opacity("Sheer amount",Range(.05,1))=.3
  _Glitter("Glitter",Range(0,4))=2.5
  _Rainbow("Rainbow per meter of height",Range(0,.1))=.0044
  _SparkleGlow("Sparkle bloom",Range(1,12))=6
 }
 SubShader {Tags {"Queue"="Transparent-5" "RenderType"="Transparent"} Blend SrcAlpha OneMinusSrcAlpha ZWrite Off Cull Back
 Pass {CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #pragma multi_compile_instancing
 #include "UnityCG.cginc"
 #include "AstraStorm.cginc"
 struct appdata {float4 vertex:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;UNITY_VERTEX_INPUT_INSTANCE_ID};
 struct v2f {float4 pos:SV_POSITION;float3 world:TEXCOORD0;float3 normal:TEXCOORD1;UNITY_VERTEX_OUTPUT_STEREO};
 float4 _Color;float _Hue,_Opacity,_Glitter,_Rainbow,_SparkleGlow;
 float3 HueShift(float3 c,float a){float3 k=float3(.57735,.57735,.57735);float ca=cos(a);return c*ca+cross(k,c)*sin(a)+k*dot(k,c)*(1-ca);}
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
 v2f vert(appdata v){v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.pos=UnityObjectToClipPos(v.vertex);o.world=mul(unity_ObjectToWorld,v.vertex).xyz;o.normal=UnityObjectToWorldNormal(v.normal);return o;}
 half4 frag(v2f i):SV_Target{UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
  // Height-driven hue with uneven drift, plus a soft gradient across each step, so no two floors look alike.
  float y=i.world.y;
  float hue=_Hue+y*_Rainbow+.09*sin(y*.0166+1.3)+.06*sin(y*.0062+4.1);
  hue+=.014*sin(atan2(i.world.z,i.world.x)*2+y*.01)+.04*(length(i.world.xz)-4.3);
  float3 col=HueShift(_Color.rgb,hue*6.2832);
  float3 eye=normalize(_WorldSpaceCameraPos-i.world);float3 n=normalize(i.normal);
  float sheen=pow(1-saturate(abs(dot(n,eye))),2);
  float3 p=i.world;
  float g=Glints(p*140,2.1,.55)+Glints(p*55+17.3,1.3,.4)*1.3+Glints(p*22+41.9,.9,.25)*1.6;
  float3 sparkle=lerp(float3(1,.92,1),.65+.35*cos(float3(0,2.1,4.2)+Hash3(floor(p*55))*6.28),.35);
  float fade=1-smoothstep(55,66,abs(i.world.y-_WorldSpaceCameraPos.y));
  float3 rgb=col*(.75+.6*sheen)+sparkle*g*_Glitter*_SparkleGlow; // HDR: sparkles go well above the 1.1 bloom threshold
  return half4(StormDim(rgb),saturate(_Opacity+sheen*.25+g*1.6)*fade);
 }
 ENDCG }
 }
}
