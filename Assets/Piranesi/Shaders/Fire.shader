// Torch flames: crossed vertical quads (uv 0..1, v up) drawn additively; the flame shape flickers with scrolling noise.
Shader "Piranesi/Fire"
{
    Properties
    {
        _NoiseTex ("Noise", 2D) = "gray" {}
        _Inner ("Inner colour", Color) = (1.0, 0.86, 0.55, 1)
        _Outer ("Outer colour", Color) = (1.0, 0.36, 0.08, 1)
        _Intensity ("Intensity", Float) = 3.5
        _Speed ("Speed", Float) = 1.6
    }
    SubShader
    {
        Tags { "Queue"="Transparent+10" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend One One
        ZWrite Off
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            sampler2D _NoiseTex; float4 _Inner, _Outer; float _Intensity, _Speed;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float seed : TEXCOORD1; UNITY_FOG_COORDS(2) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 origin = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                o.seed = PHash13(floor(origin * 7.3));
                float t = _Time.y * _Speed + o.seed * 20.0;
                float4 p = v.vertex;
                p.x += sin(t * 2.3 + p.y * 6.0) * 0.03 * v.uv.y;          // the tip sways
                p.z += cos(t * 1.9 + p.y * 5.0) * 0.03 * v.uv.y;
                o.pos = UnityObjectToClipPos(p); o.uv = v.uv;
                UNITY_TRANSFER_FOG(o, o.pos); return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float t = _Time.y * _Speed + i.seed * 20.0;
                float2 uv = i.uv;
                float n1 = tex2D(_NoiseTex, float2(uv.x * 1.3 + i.seed, uv.y * 0.9 - t * 0.9)).r;
                float n2 = tex2D(_NoiseTex, float2(uv.x * 2.7 - i.seed, uv.y * 1.8 - t * 1.6)).r;
                float n = n1 * 0.6 + n2 * 0.4;
                float x = (uv.x - 0.5) * 2.0;
                float width = (1.0 - uv.y) * 0.85 + 0.12;                   // teardrop: wide at the base, a point at the top
                float shape = saturate(1.0 - abs(x) / max(width * (0.6 + 0.6 * n), 0.02));
                shape *= saturate(uv.y * 6.0) * saturate((1.0 - uv.y) * 1.6 + (n - 0.5) * 0.9);
                float core = saturate(shape * 1.8 - 0.8) * saturate(1.2 - uv.y * 1.4);
                float flick = 0.85 + 0.15 * sin(t * 11.0) * sin(t * 7.3 + 1.7);
                float3 col = lerp(_Outer.rgb, _Inner.rgb, core) * shape * _Intensity * flick * lerp(1.0, 1.35, _UdonNight);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, col, fixed4(0, 0, 0, 0));
                return fixed4(col, 1);
            }
            ENDCG
        }
    }
}
