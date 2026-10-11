// The End Show's hyperspace dive: the inside of a long tube round the player. Star streaks rush past and bands of the six
// road colours roll down the tunnel. HouseStorm drives _Amount (0 off .. 1 full) and _Rush (streak speed).
Shader "Piranesi/Warp"
{
    Properties
    {
        _Amount ("Amount", Range(0, 1)) = 0
        _Rush ("Rush", Range(0, 4)) = 1
        _C0 ("Road 1", Color) = (0.24, 0.55, 1, 1)
        _C1 ("Road 2", Color) = (1, 0.35, 0.21, 1)
        _C2 ("Road 3", Color) = (0.64, 0.36, 1, 1)
        _C3 ("Road 4", Color) = (1, 0.7, 0.12, 1)
        _C4 ("Road 5", Color) = (0.18, 0.91, 0.54, 1)
        _C5 ("Road 6", Color) = (1, 0.31, 0.66, 1)
    }
    SubShader
    {
        Tags { "Queue"="Transparent+50" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend One One ZWrite Off ZTest Always Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            float _Amount, _Rush; float4 _C0, _C1, _C2, _C3, _C4, _C5;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
            float H(float n) { return frac(sin(n * 127.1 + 311.7) * 43758.5453); }
            float3 Road(float k)
            {
                k = fmod(k, 6.0);
                return k < 1 ? _C0.rgb : k < 2 ? _C1.rgb : k < 3 ? _C2.rgb : k < 4 ? _C3.rgb : k < 5 ? _C4.rgb : _C5.rgb;
            }
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.uv; return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_Amount <= 0) return 0;
                float t = _Time.y * _Rush;
                // streaks: thin columns, each with its own speed and length, rushing up the tube (you fall down it)
                float cols = 220; float col = floor(i.uv.x * cols); float h = H(col);
                float across = pow(saturate(1 - abs(frac(i.uv.x * cols) * 2 - 1)), 6);
                float s = frac(i.uv.y * (1.5 + 3 * h) + t * (0.8 + 1.6 * H(col + 7.3)) + h * 9);
                float streak = smoothstep(1 - (0.05 + 0.2 * H(col + 3.1)), 1, s) * across;
                // bands of the six road colours rolling down the tunnel
                float b = i.uv.y * 3 + t * 0.35 + i.uv.x * 0.5;
                float3 band = Road(floor(b)) * pow(saturate(1 - abs(frac(b) * 2 - 1)), 3) * 0.45;
                float ends = smoothstep(0, 0.2, i.uv.y) * smoothstep(1, 0.8, i.uv.y);
                float3 c = (band + float3(1, 0.97, 1.05) * streak * 2.5 * (0.6 + 0.4 * h)) * ends * _Amount;
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
