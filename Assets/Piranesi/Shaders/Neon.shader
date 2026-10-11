// The colour key: a glowing band of neon glitter in one road's colour. Used for the rings round the foot of the family
// pedestals, the painted bands on the mooring poles and the six river floater tubes on the roofs. Glints use Astra's
// 3D-cell sparkles (findastra/astras-infinite-pole, GlitterCloud), so every sparkle is round on any surface. Brighter
// at night; HDR so it blooms. Instanced (one material per road), no textures.
Shader "Piranesi/Neon"
{
    Properties
    {
        _Color ("Road colour", Color) = (1, 0.31, 0.66, 1)
        _Glow ("Glow", Range(0, 6)) = 2.2
        _Core ("White-hot core", Range(0, 1)) = 0.35
        _Glitter ("Glitter", Range(0, 4)) = 2.0
        _Pulse ("Pulse", Range(0, 1)) = 0.2
    }
    SubShader
    {
        Tags { "Queue"="Geometry" "RenderType"="Opaque" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            float4 _Color; float _Glow, _Core, _Glitter, _Pulse;
            struct appdata { float4 vertex : POSITION; float3 normal : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 world : TEXCOORD0; float3 normal : TEXCOORD1; float seed : TEXCOORD2; UNITY_FOG_COORDS(3) UNITY_VERTEX_OUTPUT_STEREO };
            float Hash3(float3 p) { return frac(sin(dot(p, float3(127.1, 311.7, 74.7))) * 43758.5453); }
            float Glints(float3 p, float speed, float density)
            {
                float3 cell = floor(p); float h = Hash3(cell); float3 f = frac(p) - 0.5;
                float3 off = float3(Hash3(cell + 3.1), Hash3(cell + 7.7), Hash3(cell + 5.3)) - 0.5;
                float spot = pow(saturate(1 - length(f - off * 0.6) * 2.6), 4);
                float flash = pow(saturate(0.5 + 0.5 * sin(_Time.y * speed + h * 63)), 10);
                return spot * flash * step(1 - density, h) * saturate(1 - length(fwidth(p)) * 0.35);
            }
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.world = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.normal = UnityObjectToWorldNormal(v.normal);
                o.seed = PHash13(floor(mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz * 1.7));
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 n = normalize(i.normal); float3 eye = normalize(_WorldSpaceCameraPos - i.world);
                float facing = saturate(dot(n, eye));
                float pulse = 1 + _Pulse * sin(_Time.y * 2.1 + i.seed * 40);
                float3 base = _Color.rgb * (0.55 + 0.45 * pow(1 - facing, 1.5));
                base = lerp(base, float3(1, 1, 1) * max(max(_Color.r, _Color.g), _Color.b), _Core * pow(facing, 6));
                float g = Glints(i.world * 70, 1.9, 0.5) + Glints(i.world * 26 + 9.1, 1.2, 0.35) * 1.3;
                float3 c = base * _Glow * pulse * lerp(1.0, 1.45, _UdonNight) + lerp(float3(1, 1, 1), _Color.rgb, 0.3) * g * _Glitter * 3.0;
                UNITY_APPLY_FOG(i.fogCoord, c);
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
