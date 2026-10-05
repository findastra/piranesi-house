// Old leaded window glass: faintly tinted, Fresnel reflection of the baked probes, a hard sun glint and a
// slight waviness so the view through it is never perfectly flat.
Shader "Piranesi/Glass"
{
    Properties
    {
        _Color ("Tint (A = opacity)", Color) = (0.82, 0.92, 0.94, 0.06)
        _Reflect ("Reflection", Range(0,1)) = 0.7
        _NoiseTex ("Noise", 2D) = "gray" {}
        _Wave ("Waviness", Range(0,0.2)) = 0.06
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend One OneMinusSrcAlpha
        ZWrite Off
        Cull Off
        Pass
        {
            Tags { "LightMode"="ForwardBase" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            #include "PiranesiCommon.cginc"
            sampler2D _NoiseTex; float4 _Color; float _Reflect, _Wave;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 wp : TEXCOORD0; float3 wn : TEXCOORD1; UNITY_FOG_COORDS(2) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.wn = UnityObjectToWorldNormal(v.normal);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float3 V = normalize(_WorldSpaceCameraPos - i.wp);
                float3 N = normalize(i.wn);
                N = dot(N, V) < 0 ? -N : N;
                float2 nuv = float2(i.wp.x + i.wp.z, i.wp.y) * 0.35;
                float2 w = (tex2D(_NoiseTex, nuv).rg - 0.5) * _Wave;
                N = normalize(N + float3(w.x, w.y, -w.x));
                float ndv = saturate(dot(N, V));
                float fres = 0.04 + 0.96 * pow(1.0 - ndv, 5.0);
                float3 R = reflect(-V, N);
                float3 refl = DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0, R, 1.0), unity_SpecCube0_HDR);
                refl *= (_UdonReflDim > 0.001 ? _UdonReflDim : 1.0);
                float3 L = normalize(_WorldSpaceLightPos0.xyz);
                float spec = pow(saturate(dot(N, normalize(L + V))), 400.0) * 3.0;
                float3 col = _Color.rgb * _Color.a * ShadeSH9(float4(N, 1)) + refl * fres * _Reflect + spec * _LightColor0.rgb;
                float a = saturate(_Color.a + fres * _Reflect * 0.6 + spec);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, col, fixed4(0, 0, 0, 0));
                return fixed4(col, a);
            }
            ENDCG
        }
    }
}
