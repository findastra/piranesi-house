// vine-bloomer: the ivy mantle over roofs and outer walls. A tiled, Blender-rendered ivy carpet (albedo + alpha,
// leaf normals, mask R smooth / G occlusion / B per-leaf rank). Vertex colour A = coverage: where it falls, the
// lower leaves drop out first, so the mantle thins leaf by leaf instead of ending on a straight edge.
Shader "Piranesi/IvyMat"
{
    Properties
    {
        _Color ("Tint", Color) = (1,1,1,1)
        _MainTex ("Ivy carpet (A = leaf)", 2D) = "white" {}
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _MaskTex ("Mask (R smooth, G ao, B leaf rank)", 2D) = "white" {}
        _Cutoff ("Leaf alpha cutoff", Range(0,1)) = 0.5
        _Smoothness ("Smoothness", Range(0,1)) = 0.75
        _Translucency ("Translucency", Range(0,2)) = 0.7
        _Caustics ("Caustics", 2D) = "black" {}
        _CausticStrength ("Caustic strength", Range(0,6)) = 1
    }
    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "Queue"="AlphaTest" }
        Cull Back
        CGPROGRAM
        #pragma surface surf StandardIvy fullforwardshadows addshadow
        #pragma target 3.5
        #pragma multi_compile_instancing
        #include "UnityPBSLighting.cginc"
        #include "PiranesiSurface.cginc"
        sampler2D _MainTex, _BumpMap, _MaskTex;
        float4 _Color; float _Cutoff, _Smoothness, _Translucency;
        struct Input { float2 uv_MainTex; float3 worldPos; float4 color : COLOR; };
        struct SurfaceOutputIvy { fixed3 Albedo; fixed3 Normal; half3 Emission; half Metallic; half Smoothness; half Occlusion; fixed Alpha; half Trans; };

        inline half4 LightingStandardIvy(SurfaceOutputIvy s, half3 viewDir, UnityGI gi)
        {
            SurfaceOutputStandard so; so.Albedo = s.Albedo; so.Normal = s.Normal; so.Emission = s.Emission;
            so.Metallic = 0; so.Smoothness = s.Smoothness; so.Occlusion = s.Occlusion; so.Alpha = s.Alpha;
            half4 c = LightingStandard(so, viewDir, gi);
            half3 L = gi.light.dir;
            half back = pow(saturate(dot(viewDir, -L)), 4.0) * 0.6;
            c.rgb += s.Albedo * gi.light.color * back * s.Trans;
            return c;
        }
        inline void LightingStandardIvy_GI(SurfaceOutputIvy s, UnityGIInput d, inout UnityGI gi)
        {
            SurfaceOutputStandard so; so.Albedo = s.Albedo; so.Normal = s.Normal; so.Emission = s.Emission;
            so.Metallic = 0; so.Smoothness = s.Smoothness; so.Occlusion = s.Occlusion; so.Alpha = s.Alpha;
            LightingStandard_GI(so, d, gi);
        }

        void surf (Input IN, inout SurfaceOutputIvy o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            clip(c.a - _Cutoff);
            fixed4 m = tex2D(_MaskTex, IN.uv_MainTex);
            // thinning: a leaf survives while its rank beats the local lack of cover
            clip(m.b - ((1.0 - IN.color.a) * 0.85 + 0.1));
            float smooth = m.r * _Smoothness;
            float3 alb = c.rgb;
            float under = PiranesiWet(IN.worldPos, alb, smooth);
            alb = lerp(alb, float3(0.85, 0.9, 0.95), _UdonSnow * 0.25);
            o.Albedo = alb;
            o.Normal = UnpackNormal(tex2D(_BumpMap, IN.uv_MainTex));
            o.Smoothness = smooth;
            o.Occlusion = m.g * lerp(0.75, 1.0, IN.color.r);
            o.Alpha = 1;
            o.Trans = _Translucency;
            o.Emission = PiranesiCaustics(IN.worldPos, float3(0,1,0), alb, under);
        }
        ENDCG
    }
    FallBack "Legacy Shaders/Transparent/Cutout/VertexLit"
}
