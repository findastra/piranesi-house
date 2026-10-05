// Leaves, fronds, ivy and flowers: alpha clip, two-sided, wind sway, backlit translucency.
Shader "Piranesi/Foliage"
{
    Properties
    {
        _Color ("Tint", Color) = (1,1,1,1)
        _MainTex ("Albedo (A = alpha)", 2D) = "white" {}
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _MaskTex ("Mask (R smooth, G ao)", 2D) = "white" {}
        _Cutoff ("Alpha cutoff", Range(0,1)) = 0.45
        _Smoothness ("Smoothness", Range(0,1)) = 0.6
        _Wind ("Wind strength", Range(0,2)) = 0.4
        _WindScale ("Wind height scale (m)", Float) = 2
        _Translucency ("Translucency", Range(0,2)) = 0.6
        _VertexTint ("Vertex colour tint (G,B,A = rgb)", Range(0,1)) = 0
        _Caustics ("Caustics", 2D) = "black" {}
        _CausticStrength ("Caustic strength", Range(0,6)) = 1
    }
    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "Queue"="AlphaTest" "DisableBatching"="LODFading" }
        Cull Off
        CGPROGRAM
        #pragma surface surf StandardFoliage fullforwardshadows addshadow vertex:vert
        #pragma target 3.5
        #pragma multi_compile_instancing
        #include "UnityPBSLighting.cginc"
        #include "PiranesiSurface.cginc"
        sampler2D _MainTex, _BumpMap, _MaskTex;
        float4 _Color; float _Cutoff, _Smoothness, _Wind, _WindScale, _Translucency, _VertexTint;
        struct Input { float2 uv_MainTex; float3 worldPos; float4 color : COLOR; float facing : VFACE; };
        struct SurfaceOutputFoliage { fixed3 Albedo; fixed3 Normal; half3 Emission; half Metallic; half Smoothness; half Occlusion; fixed Alpha; half Trans; };

        void vert (inout appdata_full v)
        {
            float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
            float h = saturate(abs(v.vertex.y) / max(_WindScale, 0.01));   // hanging vines (y < 0) sway too
            float t = _Time.y;
            float gust = 0.6 + 0.4 * sin(t * 0.7 + wp.x * 0.05 + wp.z * 0.04);
            float3 sway = float3(sin(t * 1.3 + wp.x * 0.4 + wp.y), 0, cos(t * 1.1 + wp.z * 0.4)) * 0.05;
            float flutter = sin(t * 6.0 + dot(wp, float3(3.1, 2.3, 4.7))) * 0.012;
            v.vertex.xyz += mul((float3x3)unity_WorldToObject, (sway * h * h + flutter * v.normal) * _Wind * gust);
        }

        inline half4 LightingStandardFoliage(SurfaceOutputFoliage s, half3 viewDir, UnityGI gi)
        {
            SurfaceOutputStandard so; so.Albedo = s.Albedo; so.Normal = s.Normal; so.Emission = s.Emission;
            so.Metallic = 0; so.Smoothness = s.Smoothness; so.Occlusion = s.Occlusion; so.Alpha = s.Alpha;
            half4 c = LightingStandard(so, viewDir, gi);
            // light coming through the leaf from behind
            half3 L = gi.light.dir;
            half back = pow(saturate(dot(viewDir, -L)), 4.0) * 0.8 + saturate(dot(-s.Normal, L)) * 0.4;
            c.rgb += s.Albedo * gi.light.color * back * s.Trans;
            return c;
        }
        inline void LightingStandardFoliage_GI(SurfaceOutputFoliage s, UnityGIInput d, inout UnityGI gi)
        {
            SurfaceOutputStandard so; so.Albedo = s.Albedo; so.Normal = s.Normal; so.Emission = s.Emission;
            so.Metallic = 0; so.Smoothness = s.Smoothness; so.Occlusion = s.Occlusion; so.Alpha = s.Alpha;
            LightingStandard_GI(so, d, gi);
        }

        void surf (Input IN, inout SurfaceOutputFoliage o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            clip(c.a - _Cutoff);
            fixed4 m = tex2D(_MaskTex, IN.uv_MainTex);
            float3 n = UnpackNormal(tex2D(_BumpMap, IN.uv_MainTex));
            n.z *= IN.facing > 0 ? 1 : -1;
            float smooth = m.r * _Smoothness;
            float3 alb = c.rgb * lerp(float3(1, 1, 1), IN.color.gba, _VertexTint);
            float under = PiranesiWet(IN.worldPos, alb, smooth);
            // a touch of frost in winter
            alb = lerp(alb, float3(0.85, 0.9, 0.95), _UdonSnow * 0.25);
            o.Albedo = alb;
            o.Normal = n;
            o.Smoothness = smooth;
            o.Occlusion = m.g * lerp(0.6, 1.0, IN.color.r);
            o.Alpha = 1;
            o.Trans = _Translucency;
            o.Emission = PiranesiCaustics(IN.worldPos, float3(0,1,0), alb, under);
        }
        ENDCG
    }
    FallBack "Legacy Shaders/Transparent/Cutout/VertexLit"
}
