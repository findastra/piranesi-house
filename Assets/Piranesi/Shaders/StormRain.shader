// Ported unchanged from findastra/astras-infinite-pole (theatre branch, Assets/Astra/Shaders/StormRain.shader) for the House's Stormscape.
Shader "Astra/Storm Rain" {
 // Claude 2026-10-01: thin soft rain streaks for the Stormscape particles; lightning brightens them.
 Properties { _Tint("Tint",Color)=(.7,.75,.88,.42) }
 SubShader {Tags {"Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True"} Blend SrcAlpha OneMinusSrcAlpha ZWrite Off Cull Off
 Pass {CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #include "UnityCG.cginc"
 #include "AstraStorm.cginc"
 float4 _Tint;
 struct appdata{float4 vertex:POSITION;float2 uv:TEXCOORD0;float4 color:COLOR;UNITY_VERTEX_INPUT_INSTANCE_ID};
 struct v2f{float4 pos:SV_POSITION;float2 uv:TEXCOORD0;float4 color:COLOR;UNITY_VERTEX_OUTPUT_STEREO};
 v2f vert(appdata v){v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.pos=UnityObjectToClipPos(v.vertex);o.uv=v.uv;o.color=v.color;return o;}
 half4 frag(v2f i):SV_Target{UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
  // soft both ways, so it looks right whichever way the stretched billboard maps its UVs (the quad itself is long and thin)
  float a=pow(1-abs(i.uv.x*2-1),1.4)*pow(1-abs(i.uv.y*2-1),1.4)*_Tint.a*i.color.a*1.8;
  float3 c=_Tint.rgb*i.color.rgb+float3(.6,.65,.9)*_UdonFlash;
  return half4(c,a);
 }
 ENDCG}}
}
