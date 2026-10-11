// Ported unchanged from findastra/astras-infinite-pole (theatre branch, Assets/Astra/Shaders/StormSky.shader) for the House's Stormscape.
Shader "Astra/Storm Sky" {
 // Claude 2026-10-01: Stormscape sky. Heavy rolling storm clouds in greys and blacks with a faint dark rainbow sheen,
 // moving fast, lit from inside by lightning (_UdonFlash from AstraStorm.cs).
 Properties {
  _Speed("Cloud speed",Float)=.035
  _Exposure("Exposure",Range(0,2))=1
 }
 SubShader {Tags {"Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox"} Cull Off ZWrite Off
 Pass {CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #include "UnityCG.cginc"
 #include "AstraStorm.cginc"
 float _Speed,_Exposure;
 struct appdata{float4 vertex:POSITION;UNITY_VERTEX_INPUT_INSTANCE_ID};
 struct v2f{float4 pos:SV_POSITION;float3 dir:TEXCOORD0;UNITY_VERTEX_OUTPUT_STEREO};
 float H(float3 p){p=frac(p*.3183099+.1);p*=17;return frac(p.x*p.y*p.z*(p.x+p.y+p.z));}
 float N(float3 p){float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);
  return lerp(lerp(lerp(H(i),H(i+float3(1,0,0)),f.x),lerp(H(i+float3(0,1,0)),H(i+float3(1,1,0)),f.x),f.y),
              lerp(lerp(H(i+float3(0,0,1)),H(i+float3(1,0,1)),f.x),lerp(H(i+float3(0,1,1)),H(i+float3(1,1,1)),f.x),f.y),f.z);}
 float F(float3 p){float v=0,a=.5;for(int k=0;k<5;k++){v+=a*N(p);p=p*2.07+float3(1.7,9.2,4.1);a*=.5;}return v;}
 v2f vert(appdata v){v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.pos=UnityObjectToClipPos(v.vertex);o.dir=v.vertex.xyz;return o;}
 half4 frag(v2f i):SV_Target{UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
  float3 d=normalize(i.dir);float h=d.y;float t=_Time.y*_Speed;
  // project onto a low cloud deck so the clouds flatten toward the horizon
  float3 p=float3(d.x,0,d.z)/max(abs(h)+.12,.12)*1.6+float3(t*2.2,t*.6,t*1.4);
  float c1=F(p),c2=F(p*1.9+float3(4.2,1.3,7.7)-t*.8);
  float dense=smoothstep(.35,.75,c1*.65+c2*.45);
  float3 rb=StormRainbow(c1*.9+d.x*.15+t*.3);
  float3 dark=float3(.012,.012,.017),mid=float3(.11,.11,.135);
  float3 col=lerp(mid,dark,dense)*lerp(float3(1,1,1),rb*1.7,.35);
  col+=float3(.16,.16,.2)*pow(saturate(1-dense),3)*.45;                         // thin gaps glow a little
  col=lerp(col,STORM_HORIZON,smoothstep(.22,0,abs(h)));                           // haze down to the horizon (matches the sea)
  col+=float3(.55,.6,.85)*_UdonFlash*(.35+.9*(1-dense))*(.6+.4*saturate(h*2+.4)); // lightning lights the cloud deck
  return half4(col*_Exposure,1);
 }
 ENDCG}}
}
