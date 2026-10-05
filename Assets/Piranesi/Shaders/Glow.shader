// Soft camera-facing halo for lanterns (quad mesh, billboarded in the vertex shader).
Shader "Piranesi/Glow"
{
    Properties { _Color ("Color", Color) = (1, 0.65, 0.35, 1) _Size ("Size", Float) = 1.2 _Intensity ("Intensity", Float) = 0.6 }
    SubShader
    {
        Tags { "Queue"="Transparent+5" "RenderType"="Transparent" "IgnoreProjector"="True" "DisableBatching"="True" }
        Blend One One ZWrite Off Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            float4 _Color; float _Size, _Intensity;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float seed : TEXCOORD1; UNITY_FOG_COORDS(2) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 origin = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float4 vp = mul(UNITY_MATRIX_V, float4(origin, 1));
                vp.xy += (v.uv - 0.5) * _Size;
                vp.z += 0.15;
                o.pos = mul(UNITY_MATRIX_P, vp);
                o.uv = v.uv;
                o.seed = PHash13(floor(origin * 3.1));
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float r = length(i.uv - 0.5) * 2.0;
                float g = exp(-r * r * 5.0) * saturate(1.0 - r);
                float fl = 0.85 + 0.15 * sin(_Time.y * 9.0 + i.seed * 20.0);
                float3 c = _Color.rgb * g * _Intensity * fl * lerp(0.6, 1.5, _UdonNight);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(0, 0, 0, 0));
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
