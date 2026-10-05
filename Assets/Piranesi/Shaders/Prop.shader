// UV-mapped PBR for scanned props (Poly Haven / Smithsonian): albedo, GL normal, mask (R smooth, G ao, B metal).
// Gets wet under the tide line, receives caustics, optional alpha clip and two-sided.
Shader "Piranesi/Prop"
{
    Properties
    {
        _Color ("Tint", Color) = (1,1,1,1)
        _MainTex ("Albedo (A = alpha)", 2D) = "white" {}
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _MaskTex ("Mask (R smooth, G ao, B metal)", 2D) = "white" {}
        _Smoothness ("Smoothness", Range(0,1.5)) = 1
        _Metallic ("Metallic scale", Range(0,1)) = 1
        _Cutoff ("Alpha cutoff", Range(0,1)) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        _Caustics ("Caustics", 2D) = "black" {}
        _CausticStrength ("Caustic strength", Range(0,6)) = 2
        _VertexAO ("Vertex AO", Range(0,1)) = 0.5
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Cull [_Cull]
        CGPROGRAM
        #pragma surface surf StandardPiranesi fullforwardshadows addshadow
        #pragma target 3.5
        #pragma multi_compile_instancing
        #include "UnityPBSLighting.cginc"
        #include "PiranesiSurface.cginc"
        sampler2D _MainTex, _BumpMap, _MaskTex;
        float4 _Color; float _Smoothness, _Metallic, _Cutoff, _VertexAO;
        struct Input { float2 uv_MainTex; float3 worldPos; float4 color : COLOR; float3 worldNormal; INTERNAL_DATA };
        inline half4 LightingStandardPiranesi(SurfaceOutputStandard s, half3 v, UnityGI gi) { return LightingStandard(s, v, gi); }
        inline void LightingStandardPiranesi_GI(SurfaceOutputStandard s, UnityGIInput d, inout UnityGI gi)
        { LightingStandard_GI(s, d, gi); gi.indirect.specular *= (_UdonReflDim > 0.001 ? _UdonReflDim : 1.0); }
        void surf (Input IN, inout SurfaceOutputStandard o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            if (_Cutoff > 0) clip(c.a - _Cutoff);
            fixed4 m = tex2D(_MaskTex, IN.uv_MainTex);
            float3 alb = c.rgb;
            float smooth = saturate(m.r * _Smoothness);
            float3 wn = WorldNormalVector(IN, float3(0,0,1));
            float under = PiranesiWet(IN.worldPos, alb, smooth);
            alb = PiranesiUnderwaterTint(IN.worldPos, alb);
            o.Albedo = alb;
            o.Normal = UnpackNormal(tex2D(_BumpMap, IN.uv_MainTex));
            o.Smoothness = smooth;
            o.Metallic = m.b * _Metallic;
            o.Occlusion = m.g * lerp(1.0, IN.color.r, _VertexAO);
            o.Emission = PiranesiCaustics(IN.worldPos, wn, alb, under);
        }
        ENDCG
    }
    FallBack "Diffuse"
}
