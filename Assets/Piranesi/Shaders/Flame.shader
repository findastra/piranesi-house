// Lantern glass / flame: flickering HDR emission (drives bloom).
Shader "Piranesi/Flame"
{
    Properties { _Color ("Color", Color) = (1, 0.62, 0.3, 1) _Intensity ("Intensity", Float) = 5 }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            float4 _Color; float _Intensity;
            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float seed : TEXCOORD0; float h : TEXCOORD1; UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                float3 origin = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                o.seed = PHash13(floor(origin * 3.1));
                o.h = v.vertex.y;
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float t = _Time.y;
                float fl = 0.82 + 0.1 * sin(t * 11.0 + i.seed * 30.0) + 0.08 * sin(t * 23.0 + i.seed * 7.0);
                float night = lerp(0.8, 1.4, _UdonNight);
                return fixed4(_Color.rgb * _Intensity * fl * night, 1);
            }
            ENDCG
        }
    }
}
