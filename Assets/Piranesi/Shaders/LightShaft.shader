// Volumetric-looking god ray. Mesh: open cylinder from y=0 (opening) to y=-1. Object scale x = radius,
// y = height of the opening above the floor. The shaft is sheared along the live sun/moon direction.
Shader "Piranesi/LightShaft"
{
    Properties
    {
        _NoiseTex ("Noise", 2D) = "gray" {}
        _Intensity ("Intensity", Float) = 0.35
        _UseFacing ("Window (only lit when light enters)", Float) = 0
        _Spread ("Spread", Float) = 0.25
        _Tint ("Tint", Color) = (1, 0.97, 0.9, 1)
        _Vertical ("Force vertical (spotlit shafts)", Float) = 0
    }
    SubShader
    {
        Tags { "Queue"="Transparent+10" "RenderType"="Transparent" "IgnoreProjector"="True" "DisableBatching"="True" }
        Blend One One
        ZWrite Off
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            sampler2D _NoiseTex; float _Intensity, _UseFacing, _Spread, _Vertical; float4 _Tint;
            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 wp : TEXCOORD0; float3 nw : TEXCOORD1; float t : TEXCOORD2; float facing : TEXCOORD3; UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 origin = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float radius = length(unity_ObjectToWorld._m00_m10_m20);
                float height = length(unity_ObjectToWorld._m01_m11_m21);
                float3 fwd = normalize(unity_ObjectToWorld._m02_m12_m22);
                float3 travel = -normalize(_UdonLightDir.xyz + float3(0, 1e-4, 0));
                travel.y = min(travel.y, -0.3);
                travel = normalize(lerp(normalize(travel), float3(0, -1, 0), _Vertical));
                float t = saturate(-v.vertex.y);
                float len = height / -travel.y;
                float3 ring = float3(v.vertex.x, 0, v.vertex.z);
                float3 wp = origin + ring * radius * (1.0 + t * _Spread) + travel * len * t;
                o.wp = wp;
                o.nw = normalize(ring + 1e-4);
                o.t = t;
                float2 th = normalize(travel.xz + 1e-4);
                o.facing = lerp(1.0, saturate(dot(th, normalize(fwd.xz + 1e-4)) * 1.5), _UseFacing);
                o.pos = mul(UNITY_MATRIX_VP, float4(wp, 1));
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float3 V = normalize(_WorldSpaceCameraPos - i.wp);
                float edge = pow(saturate(abs(dot(i.nw, V))), 1.6);
                float fade = smoothstep(0.0, 0.06, i.t) * (1.0 - smoothstep(0.6, 1.0, i.t));
                float n = tex2D(_NoiseTex, float2(atan2(i.nw.z, i.nw.x) * 0.5 + _Time.y * 0.01, i.t * 0.4 - _Time.y * 0.02)).r;
                float camFade = saturate((distance(_WorldSpaceCameraPos, i.wp) - 0.8) / 4.0);
                float aboveWater = saturate((i.wp.y - _UdonTide) * 4.0);
                float3 c = max(_UdonSunColor.rgb, 0.0) * _Tint.rgb * _Intensity * _UdonShaft * edge * fade * camFade * i.facing * (0.55 + 0.6 * n) * aboveWater;
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
