// Schools of small tropical fish, animated entirely on the GPU. Each school mesh holds many low-poly fish arranged round the
// object's Y axis, heading counter-clockwise. Vertex colour: R phase, G radius fraction, B body coordinate (0 tail .. 1 nose),
// A species. The school turns slowly; every fish bobs, wags its tail and is tinted by its species.
Shader "Piranesi/Fish"
{
    Properties
    {
        _Speed ("Turn speed (rad/s)", Float) = 0.25
        _Wag ("Tail wag", Float) = 0.045
        _Caustics ("Caustics", 2D) = "black" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
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
            #include "PiranesiCommon.cginc"
            float _Speed, _Wag; sampler2D _Caustics;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; float4 color : COLOR; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 wn : TEXCOORD0; float3 wp : TEXCOORD1; float2 uv : TEXCOORD2; float sp : TEXCOORD3; UNITY_FOG_COORDS(4) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 origin = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float t = _Time.y + PHash13(floor(origin)) * 50.0;
                float ph = v.color.r * 6.2832;
                float body = v.color.b;
                float3 p = v.vertex.xyz;
                // tail wag: sideways (radial from the school's axis) more toward the tail
                float2 radial = normalize(p.xz + 1e-4);
                float wag = sin(t * 9.0 + ph + body * 4.0) * _Wag * (1.0 - body);
                p.xz += radial * wag;
                // bob and breathe
                p.y += sin(t * 0.8 + ph) * 0.08;
                p.xz *= 1.0 + sin(t * 0.37 + ph) * 0.04;
                // the whole school turns counter-clockwise (inner fish a little faster)
                float a = t * _Speed * (1.15 - 0.3 * v.color.g);
                float c = cos(a), s = sin(a);
                p.xz = float2(p.x * c - p.z * s, p.x * s + p.z * c);
                float3 n = v.normal; n.xz = float2(n.x * c - n.z * s, n.x * s + n.z * c);
                o.pos = UnityObjectToClipPos(float4(p, 1));
                o.wp = mul(unity_ObjectToWorld, float4(p, 1)).xyz;
                o.wn = UnityObjectToWorldNormal(n);
                o.uv = v.uv; o.sp = v.color.a * 4.0 - 0.25;
                UNITY_TRANSFER_FOG(o, o.pos); return o;
            }
            float3 Palette(float sp, float u, float v)
            {
                // 0 yellow tang, 1 blue tang, 2 clownfish, 3 blue-green chromis
                float3 c;
                if (sp < 0.5) c = lerp(float3(1.0, 0.86, 0.05), float3(1.0, 0.95, 0.6), step(0.92, u));
                else if (sp < 1.5)
                {
                    c = float3(0.06, 0.22, 0.85);
                    c = lerp(c, float3(0.02, 0.02, 0.05), smoothstep(0.08, 0.0, abs(v - 0.62 + u * 0.15)) * step(0.25, u) * step(u, 0.8));
                    c = lerp(c, float3(1.0, 0.85, 0.1), step(u, 0.12));
                }
                else if (sp < 2.5)
                {
                    c = float3(1.0, 0.45, 0.05);
                    float band = step(abs(u - 0.75), 0.05) + step(abs(u - 0.45), 0.06) + step(abs(u - 0.15), 0.04);
                    c = lerp(c, float3(0.98, 0.98, 0.95), saturate(band));
                }
                else c = lerp(float3(0.25, 0.75, 0.85), float3(0.6, 0.95, 1.0), v);
                return c * lerp(0.75, 1.0, saturate(v + 0.3));
            }
            fixed4 frag (v2f i, fixed facing : VFACE) : SV_Target
            {
                float3 N = normalize(i.wn) * (facing > 0 ? 1 : -1);
                float3 alb = Palette(i.sp, i.uv.x, i.uv.y);
                float depth = max(_UdonTide - i.wp.y, 0.0);
                float3 L = normalize(_UdonLightDir.xyz + float3(0, 1e-4, 0));
                float3 amb = ShadeSH9(float4(0, 1, 0, 1));
                float3 sun = max(_UdonSunColor.rgb, 0.0) * saturate(dot(N, L) * 0.5 + 0.5) * exp(-depth * 0.35);
                float2 cuv = i.wp.xz * 0.32;
                float ca = min(tex2D(_Caustics, cuv + _Time.y * float2(0.031, 0.017)).r, tex2D(_Caustics, cuv * 1.37 - _Time.y * float2(0.022, -0.029)).r);
                float3 col = alb * (amb * 0.9 + sun * 0.9 + ca * 2.0 * max(_UdonSunColor.rgb, 0.0) * exp(-depth * 0.45));
                float3 absorb = exp(-depth * float3(0.30, 0.06, 0.05));
                col *= lerp(1.0, absorb, saturate(depth * 4.0));
                col += alb * 0.05;
                UNITY_APPLY_FOG(i.fogCoord, col);
                return fixed4(col, 1);
            }
            ENDCG
        }
    }
    FallBack Off
}
