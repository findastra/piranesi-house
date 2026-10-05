// Living reef colour on museum coral scans: the bleached specimen texture becomes a detail/luminance map,
// tinted from base to tip, with soft subsurface glow, depth absorption and caustics.
Shader "Piranesi/Coral"
{
    Properties
    {
        _MainTex ("Specimen albedo", 2D) = "white" {}
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _BaseColor ("Base colour", Color) = (0.55, 0.35, 0.45, 1)
        _TipColor ("Tip colour", Color) = (0.95, 0.65, 0.75, 1)
        _Height ("Colony height (m)", Float) = 1
        _Detail ("Specimen detail strength", Range(0,1)) = 0.6
        _Glow ("Subsurface glow", Range(0,1)) = 0.25
        _Smoothness ("Smoothness", Range(0,1)) = 0.35
        _Caustics ("Caustics", 2D) = "black" {}
        _CausticStrength ("Caustic strength", Range(0,6)) = 2.5
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow vertex:vert
        #pragma target 3.5
        #pragma multi_compile_instancing
        #include "PiranesiSurface.cginc"
        sampler2D _MainTex, _BumpMap;
        float4 _BaseColor, _TipColor; float _Height, _Detail, _Glow, _Smoothness;
        struct Input { float2 uv_MainTex; float3 worldPos; float objY; float3 viewDir; float3 worldNormal; INTERNAL_DATA };
        void vert (inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
            float sy = length(unity_ObjectToWorld._m01_m11_m21);
            o.objY = saturate(v.vertex.y / max(_Height, 0.01));
            // very gentle current sway for the tips
            float t = _Time.y;
            float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
            v.vertex.x += sin(t * 0.8 + wp.z * 1.3) * 0.006 * o.objY;
        }
        void surf (Input IN, inout SurfaceOutputStandard o)
        {
            float3 spec = tex2D(_MainTex, IN.uv_MainTex).rgb;
            float lum = dot(spec, float3(0.3, 0.59, 0.11));
            float3 col = lerp(_BaseColor.rgb, _TipColor.rgb, smoothstep(0.1, 0.95, IN.objY));
            col *= lerp(1.0, 0.45 + 0.9 * lum, _Detail);
            float smooth = _Smoothness;
            float3 wn = WorldNormalVector(IN, float3(0,0,1));
            float under = PiranesiWet(IN.worldPos, col, smooth);
            col = PiranesiUnderwaterTint(IN.worldPos, col);
            o.Albedo = col;
            o.Normal = UnpackNormal(tex2D(_BumpMap, IN.uv_MainTex));
            o.Smoothness = smooth;
            float rim = pow(1.0 - saturate(dot(normalize(IN.viewDir), o.Normal)), 2.0);
            o.Emission = col * _Glow * (0.35 + rim) * (ShadeSH9(float4(0,1,0,1)) + max(_UdonSunColor.rgb, 0) * 0.3)
                         + PiranesiCaustics(IN.worldPos, wn, col, under);
        }
        ENDCG
    }
    FallBack "Diffuse"
}
