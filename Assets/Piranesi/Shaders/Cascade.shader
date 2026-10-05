// Falling sheet of water pouring from a high window. Object-space mapping (mesh has no UVs).
Shader "Piranesi/Cascade"
{
    Properties { _NoiseTex ("Noise", 2D) = "gray" {} _Color ("Color", Color) = (0.75, 0.9, 0.95, 1) _Speed ("Fall speed", Float) = 1.6 }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend SrcAlpha OneMinusSrcAlpha
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
            sampler2D _NoiseTex; float4 _Color; float _Speed;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 op : TEXCOORD0; float3 wn : TEXCOORD1; float3 wp : TEXCOORD2; UNITY_FOG_COORDS(3) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.op = v.vertex.xyz;
                o.wn = UnityObjectToWorldNormal(v.normal);
                o.wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float t = _Time.y;
                float2 uv = float2(i.op.x * 0.35, i.op.y * 0.06 + t * _Speed * 0.12);
                float n1 = tex2D(_NoiseTex, uv).r;
                float n2 = tex2D(_NoiseTex, uv * float2(2.3, 1.7) + float2(0.3, t * 0.1)).a;
                float streak = smoothstep(0.35, 0.8, n1 * 0.7 + n2 * 0.5);
                float edgeX = 1.0 - smoothstep(0.35, 0.5, abs(i.op.x) / max(1.6 + (16.0 - i.op.y) * 0.05, 0.1));
                float bottom = saturate((i.wp.y - _UdonTide) * 2.0);
                float3 V = normalize(_WorldSpaceCameraPos - i.wp);
                float fres = pow(1.0 - saturate(abs(dot(normalize(i.wn), V))), 3.0);
                float3 light = ShadeSH9(float4(0, 1, 0, 1)) + max(_UdonSunColor.rgb, 0.0) * 0.6;
                float3 c = _Color.rgb * light * (0.6 + 0.9 * streak) + fres * 0.3;
                float a = saturate((0.35 + 0.65 * streak) * edgeX * bottom * _Color.a);
                UNITY_APPLY_FOG(i.fogCoord, c);
                return fixed4(c, a);
            }
            ENDCG
        }
    }
}
