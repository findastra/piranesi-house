// Astra's Infinite Pole, brought into the House for the Stormscape (from findastra/astras-infinite-pole, Shaders/InfinitePole.shader).
// Same silver body, rim, stripe and crystal sparkle; the fade now follows distance from the viewer instead of world height,
// because here the pole rises from the Colossus' palm (y 14) to 470 m.
Shader "Piranesi/AstraPole"
{
 Properties { _Opacity("Opacity",Range(0,1))=1 _Sparkle("Crystal sparkle",Range(0,4))=3 _Color("Silver tint", Color)=(0.72,0.77,0.9,1) _FadeNear("Fade start (m)",Float)=140 _FadeFar("Fade end (m)",Float)=320 }
 SubShader {
 Tags { "RenderType"="Transparent" "Queue"="Transparent-10" }
 Blend SrcAlpha OneMinusSrcAlpha
 ZWrite Off
 Pass {
  ColorMask 0
  ZWrite On
  CGPROGRAM
  #pragma vertex depthVert
  #pragma fragment depthFrag
  #pragma multi_compile_instancing
  #include "UnityCG.cginc"
  struct dIn {float4 vertex:POSITION;UNITY_VERTEX_INPUT_INSTANCE_ID};
  struct dOut {float4 pos:SV_POSITION;float d:TEXCOORD0;UNITY_VERTEX_OUTPUT_STEREO};
  float _Opacity,_FadeNear;
  dOut depthVert(dIn v){dOut o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.pos=UnityObjectToClipPos(v.vertex);o.d=distance(mul(unity_ObjectToWorld,v.vertex).xyz,_WorldSpaceCameraPos);return o;}
  fixed4 depthFrag(dOut i):SV_Target {clip(_Opacity-.99);clip(_FadeNear-i.d);return 0;}
  ENDCG
 }
 Pass {
 CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #pragma multi_compile_instancing
 #pragma multi_compile_fog
 #include "UnityCG.cginc"
 struct appdata { float4 vertex:POSITION; float3 normal:NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
 struct v2f { float4 pos:SV_POSITION; float3 normal:TEXCOORD0; float3 world:TEXCOORD1; UNITY_FOG_COORDS(2) UNITY_VERTEX_OUTPUT_STEREO };
 fixed4 _Color; float _Opacity,_Sparkle,_FadeNear,_FadeFar;
 v2f vert(appdata v) { v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o); o.pos=UnityObjectToClipPos(v.vertex); o.world=mul(unity_ObjectToWorld,v.vertex).xyz; o.normal=UnityObjectToWorldNormal(v.normal); UNITY_TRANSFER_FOG(o,o.pos); return o; }
 fixed4 frag(v2f i):SV_Target {
  UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
  float3 n=normalize(i.normal); float3 eye=normalize(_WorldSpaceCameraPos-i.world);
  float rim=pow(1-saturate(dot(n,eye)),3);
  float stripe=pow(saturate(dot(n,normalize(float3(-0.6,0,0.8)))),18);
  float3 silver=_Color.rgb*(0.18+0.7*rim+1.4*stripe);
  float fade=smoothstep(_FadeNear,_FadeFar,distance(_WorldSpaceCameraPos,i.world));
  float2 uv=float2(atan2(n.z,n.x)*12,i.world.y*95);
  float2 cell=floor(uv);float h=frac(sin(dot(cell,float2(127.1,311.7)))*43758.5453);
  float2 p=frac(uv)-.5;
  float crystal=pow(saturate(1-length(p)*2),5);
  float sparkle=crystal*pow(.5+.5*sin(_Time.y*1.1+h*60+dot(eye,n)*18),14);
  float3 gem=.6+.4*cos(float3(0,2,4)+h*6.28+_Time.y*.08);
  silver+=gem*sparkle*_Sparkle*5;
  UNITY_APPLY_FOG(i.fogCoord, silver);
  return fixed4(silver,(1-fade)*_Opacity);
 }
 ENDCG
 }
 }
}
