// Flowing water ribbons (aqueduct channel, slide flume, spouts). Uses mesh UV: u across, v along the flow.
Shader "Piranesi/WaterFlow"
{
    Properties
    {
        [Normal] _Normal0 ("Normal", 2D) = "bump" {}
        _NoiseTex ("Noise", 2D) = "gray" {}
        _Color ("Water colour", Color) = (0.55, 0.85, 0.9, 0.75)
        _Speed ("Flow speed", Float) = 1.5
        _Tiling ("Tiling (u, v)", Vector) = (1, 0.25, 0, 0)
        _Foam ("Foam", Range(0,1)) = 0.35
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend SrcAlpha OneMinusSrcAlpha
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
            sampler2D _Normal0, _NoiseTex; float4 _Color, _Tiling; float _Speed, _Foam;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float3 wn : TEXCOORD1; float3 wp : TEXCOORD2; UNITY_FOG_COORDS(3) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.uv;
                o.wn = UnityObjectToWorldNormal(v.normal); o.wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                UNITY_TRANSFER_FOG(o, o.pos); return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float t = _Time.y * _Speed;
                float2 uv = i.uv * _Tiling.xy;
                float3 n1 = UnpackNormal(tex2D(_Normal0, uv + float2(0, -t * 0.25)));
                float3 n2 = UnpackNormal(tex2D(_Normal0, uv * 1.7 + float2(0.3, -t * 0.4)));
                float3 N = normalize(i.wn + float3(n1.x + n2.x, 0, n1.y + n2.y) * 0.35);
                float3 V = normalize(_WorldSpaceCameraPos - i.wp);
                float fres = pow(1.0 - saturate(abs(dot(N, V))), 4.0);
                float3 H = normalize(_WorldSpaceLightPos0.xyz + V);
                float spec = pow(saturate(dot(N, H)), 120.0) * 2.0;
                float foamN = tex2D(_NoiseTex, uv * float2(2, 1) + float2(0, -t * 0.5)).r;
                float edge = 1.0 - saturate(min(i.uv.x, 1 - i.uv.x) * 8.0);
                float foam = saturate(smoothstep(0.55, 0.8, foamN) * _Foam + edge * 0.5);
                float3 amb = ShadeSH9(float4(0, 1, 0, 1));
                float3 col = _Color.rgb * (amb + max(_UdonSunColor.rgb, 0) * 0.5) + fres * 0.4 + spec * _LightColor0.rgb;
                col = lerp(col, (amb + max(_UdonSunColor.rgb, 0)) * 0.95, foam);
                float a = saturate(_Color.a + fres * 0.3 + foam * 0.5);
                UNITY_APPLY_FOG(i.fogCoord, col);
                return fixed4(col, a);
            }
            ENDCG
        }
    }
}
