// Astra's Celestial Sky, brought into the House for the top of the Stormscape stair (from findastra/astras-infinite-pole,
// Shaders/CelestialSky.shader). Same deep space, nebula wisps and stars; it also fades up from the whiteout (_UdonWhiteout).
Shader "Piranesi/AstraSky"
{
 Properties {
  _Zenith("Deep space",Color)=(0.012,0.008,0.045,1)
  _NebulaA("Cloud color A",Color)=(0.18,0.045,0.38,1)
  _NebulaB("Cloud color B",Color)=(0.025,0.28,0.32,1)
  _Horizon("Horizon",Color)=(0.12,0.07,0.2,1)
  _Exposure("Exposure",Range(0,2))=0.8
  _Clouds("Cloud strength",Range(0,2))=1
  _Stars("Stars",Range(0,2))=1.3
  _Seed("Constellation seed",Float)=7
 }
 SubShader {
 Tags {"Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox"}
 Cull Off ZWrite Off
 Pass { CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #pragma multi_compile_instancing
 #include "UnityCG.cginc"
 struct appdata {float4 vertex:POSITION;UNITY_VERTEX_INPUT_INSTANCE_ID};
 struct v2f {float4 pos:SV_POSITION;float3 dir:TEXCOORD0;UNITY_VERTEX_OUTPUT_STEREO};
 float4 _Zenith,_NebulaA,_NebulaB,_Horizon;
 float _Exposure,_Clouds,_Stars,_Seed;
 float _UdonWhiteout;
 v2f vert(appdata v){v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.pos=UnityObjectToClipPos(v.vertex);o.dir=v.vertex.xyz;return o;}
 float hash(float3 p){p=frac(p*0.3183099+float3(0.1,0.2,0.3));p*=17;return frac(p.x*p.y*p.z*(p.x+p.y+p.z));}
 float noise(float3 p){float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y),lerp(lerp(hash(i+float3(0,0,1)),hash(i+float3(1,0,1)),f.x),lerp(hash(i+float3(0,1,1)),hash(i+float3(1,1,1)),f.x),f.y),f.z);}
 float cloud(float3 p){return noise(p)*0.57+noise(p*2.03)*0.28+noise(p*4.11)*0.15;}
 fixed4 frag(v2f i):SV_Target {
  UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
  float3 d=normalize(i.dir);float3 p=d*3+_Seed;
  float n=cloud(p);float band=exp(-abs(d.y*0.8+d.x*0.42+0.12)*3.5);
  float wisps=pow(saturate(cloud(p*1.9+n)-0.25)*1.5,2)*band;
  float3 col=_Zenith.rgb+lerp(_NebulaA.rgb,_NebulaB.rgb,n)*wisps*_Clouds*2;
  col+=_Horizon.rgb*pow(saturate(1-abs(d.y)),8)*0.32;
  float3 cells=d*220;float3 cell=floor(cells);float seed=hash(cell+_Seed);
  float spot=1-smoothstep(0.04,0.2,length(frac(cells)-0.5));
  float star=spot*step(0.973,seed);
  col+=lerp(float3(0.62,0.77,1),float3(1,0.85,0.67),seed)*star*_Stars;
  col*=_Exposure;
  col=lerp(col,float3(0.97,0.975,1.0),saturate(_UdonWhiteout));
  return fixed4(col,1);
 }
 ENDCG }
 }
}
