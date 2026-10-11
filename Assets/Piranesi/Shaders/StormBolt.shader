// Ported unchanged from findastra/astras-infinite-pole (theatre branch, Assets/Astra/Shaders/StormBolt.shader) for the House's Stormscape.
Shader "Astra/Storm Bolt" {
 // Claude 2026-10-01: a lightning bolt card. Only visible while _UdonFlash is up, so it flickers with the flash.
 Properties { _MainTex("Bolt",2D)="black"{} _Color("Color",Color)=(.85,.9,1.3,1) }
 SubShader {Tags {"Queue"="Transparent+10" "RenderType"="Transparent" "IgnoreProjector"="True"} Blend One One ZWrite Off Cull Off
 Pass {CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #include "UnityCG.cginc"
 #include "AstraStorm.cginc"
 sampler2D _MainTex;float4 _Color;
 struct appdata{float4 vertex:POSITION;float2 uv:TEXCOORD0;UNITY_VERTEX_INPUT_INSTANCE_ID};
 struct v2f{float4 pos:SV_POSITION;float2 uv:TEXCOORD0;UNITY_VERTEX_OUTPUT_STEREO};
 v2f vert(appdata v){v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.pos=UnityObjectToClipPos(v.vertex);o.uv=v.uv;return o;}
 half4 frag(v2f i):SV_Target{UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
  float b=tex2D(_MainTex,i.uv).r;return half4(_Color.rgb*b*saturate(_UdonFlash*1.6),1);
 }
 ENDCG}}
}
