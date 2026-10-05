// Marble / stone for the whole House: world-space triplanar PBR (no UVs needed), vertex AO,
// mica sparkle, tide-wet darkening, underwater caustics, winter frost & snow.
Shader "Piranesi/Stone"
{
    Properties
    {
        _Color ("Tint", Color) = (1,1,1,1)
        _MainTex ("Albedo", 2D) = "white" {}
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _MaskTex ("Mask (R smooth, G ao, B height, A sparkle)", 2D) = "white" {}
        _Tile ("World tile size (m)", Float) = 3
        _NormalScale ("Normal strength", Range(0,2)) = 1
        _Smoothness ("Smoothness scale", Range(0,1.5)) = 1
        _Metallic ("Metallic", Range(0,1)) = 0
        _VertexAO ("Vertex AO strength", Range(0,1)) = 1
        _Sparkle ("Sparkle", Range(0,4)) = 1
        _Caustics ("Caustics", 2D) = "black" {}
        _CausticStrength ("Caustic strength", Range(0,6)) = 2
        _NoiseTex ("Noise", 2D) = "gray" {}
        _SnowAllowed ("Snow allowed", Range(0,1)) = 1
        _Blend ("Triplanar sharpness", Range(1,16)) = 8
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 300

        CGPROGRAM
        #pragma surface surf StandardPiranesi fullforwardshadows addshadow
        #pragma target 3.5
        #pragma multi_compile_instancing
        #include "UnityPBSLighting.cginc"
        #include "PiranesiCommon.cginc"

        sampler2D _MainTex, _BumpMap, _MaskTex, _Caustics, _NoiseTex;
        float _Tile, _NormalScale, _Smoothness, _Metallic, _VertexAO, _Sparkle, _CausticStrength, _SnowAllowed, _Blend;
        fixed4 _Color;

        struct Input
        {
            float3 worldPos;
            float3 worldNormal;
            float4 color : COLOR;
            INTERNAL_DATA
        };

        // dim baked reflections at night (probes are captured in daylight)
        inline half4 LightingStandardPiranesi(SurfaceOutputStandard s, half3 viewDir, UnityGI gi)
        {
            return LightingStandard(s, viewDir, gi);
        }
        inline void LightingStandardPiranesi_GI(SurfaceOutputStandard s, UnityGIInput data, inout UnityGI gi)
        {
            LightingStandard_GI(s, data, gi);
            gi.indirect.specular *= (_UdonReflDim > 0.001 ? _UdonReflDim : 1.0);
        }

        float3 WorldToTangentNormal(Input IN, float3 n)
        {
            float3 t2w0 = WorldNormalVector(IN, float3(1,0,0));
            float3 t2w1 = WorldNormalVector(IN, float3(0,1,0));
            float3 t2w2 = WorldNormalVector(IN, float3(0,0,1));
            float3x3 t2w = float3x3(t2w0, t2w1, t2w2);
            return normalize(mul(t2w, n));
        }

        void surf (Input IN, inout SurfaceOutputStandard o)
        {
            float3 wp = IN.worldPos;
            float3 wn = normalize(WorldNormalVector(IN, float3(0,0,1)));
            float3 bw = pow(abs(wn), _Blend);
            bw /= (bw.x + bw.y + bw.z + 1e-5);

            float2 uvX = wp.zy / _Tile;
            float2 uvY = wp.xz / _Tile;
            float2 uvZ = wp.xy / _Tile;
            float3 axisSign = sign(wn);
            uvX.x *= axisSign.x; uvY.x *= axisSign.y; uvZ.x *= -axisSign.z;

            fixed4 cX = tex2D(_MainTex, uvX), cY = tex2D(_MainTex, uvY), cZ = tex2D(_MainTex, uvZ);
            fixed4 mX = tex2D(_MaskTex, uvX), mY = tex2D(_MaskTex, uvY), mZ = tex2D(_MaskTex, uvZ);
            half3 nX = UnpackScaleNormal(tex2D(_BumpMap, uvX), _NormalScale);
            half3 nY = UnpackScaleNormal(tex2D(_BumpMap, uvY), _NormalScale);
            half3 nZ = UnpackScaleNormal(tex2D(_BumpMap, uvZ), _NormalScale);
            nX.x *= axisSign.x; nY.x *= axisSign.y; nZ.x *= -axisSign.z;
            // whiteout blend
            nX = half3(nX.xy + wn.zy, abs(nX.z) * wn.x);
            nY = half3(nY.xy + wn.xz, abs(nY.z) * wn.y);
            nZ = half3(nZ.xy + wn.xy, abs(nZ.z) * wn.z);
            float3 nW = normalize(nX.zyx * bw.x + nY.xzy * bw.y + nZ.xyz * bw.z);

            fixed3 albedo = (cX.rgb * bw.x + cY.rgb * bw.y + cZ.rgb * bw.z) * _Color.rgb;
            fixed4 mask = mX * bw.x + mY * bw.y + mZ * bw.z;
            float smooth = saturate(mask.r * _Smoothness);
            float vao = lerp(1.0, IN.color.r, _VertexAO);
            float occl = vao * lerp(1.0, mask.g, 0.8);

            // ---- tide: underwater + recently wet
            float depthBelow = _UdonTide - wp.y;
            float under = saturate(depthBelow * 25.0);
            float wet = saturate((_UdonWetLine - wp.y) * 6.0) * (1.0 - under);
            float wetAmt = max(wet * 0.85, under);
            albedo *= lerp(1.0, 0.68, wetAmt);
            smooth = lerp(smooth, 0.94, wetAmt);
            // faint tide-line staining
            albedo *= 1.0 - 0.06 * saturate(1.0 - abs(_UdonWetLine - wp.y) * 8.0) * (1.0 - under);

            // ---- winter: frost everywhere upward, real snow outdoors / under oculi
            float up = saturate((nW.y - 0.5) * 3.0);
            float n0 = tex2D(_NoiseTex, wp.xz * 0.21).r;
            float2 cellXZ = frac((wp.xz + 30.0) / 60.0) * 60.0 - 30.0;
            float underOculus = saturate((5.2 - length(cellXZ)) / 2.0) * step(abs(wp.x), 75.0) * step(abs(wp.z), 75.0);
            float outdoors = saturate(max(max(abs(wp.x), abs(wp.z)) - 72.0, 0.0)) + step(19.0, wp.y);
            float exposure = saturate(max(outdoors, underOculus));
            float snowM = up * _UdonSnow * _SnowAllowed * (1.0 - under) * saturate(exposure * 1.5) * smoothstep(0.25, 0.6, n0 + _UdonSnow * 0.35);
            float frost = up * _UdonSnow * 0.22 * _SnowAllowed * (1.0 - under);
            albedo = lerp(albedo, float3(0.93, 0.96, 1.0), saturate(snowM + frost));
            smooth = lerp(smooth, 0.28, snowM);
            nW = normalize(lerp(nW, wn, snowM));

            // specular anti-aliasing (Kaplanyan/Tokuyoshi style): rough up where normals vary per pixel,
            // stops the mirror-like wet marble from shimmering when the camera moves
            float3 dndx = ddx(nW), dndy = ddy(nW);
            float variance = 0.5 * (dot(dndx, dndx) + dot(dndy, dndy));
            float rough = 1.0 - smooth;
            float r2 = saturate(rough * rough + min(2.0 * variance, 0.18));
            smooth = 1.0 - sqrt(r2);

            o.Albedo = albedo;
            o.Normal = WorldToTangentNormal(IN, nW);
            o.Smoothness = smooth;
            o.Metallic = _Metallic;
            o.Occlusion = occl;

            // ---- emission: caustics under water + sparkle glints
            float t = _Time.y;
            float2 cuv = wp.xz * 0.32 + nW.xz * 0.05;
            float c1 = tex2D(_Caustics, cuv + float2(t * 0.031, t * 0.017)).r;
            float c2 = tex2D(_Caustics, cuv * 1.37 + float2(-t * 0.022, t * 0.029)).r;
            float caust = min(c1, c2) * 3.0;
            float3 sunC = max(_UdonSunColor.rgb, 0.0);
            float3 emis = caust * under * sunC * _CausticStrength * exp(-max(depthBelow, 0.0) * 0.9)
                          * saturate(nW.y * 0.7 + 0.3) * albedo;

            // mica glints: fixed in world space (no view-dependent twinkle), only where the light grazes
            // the grain, faded out with distance so they never alias into flicker
            float dist = distance(_WorldSpaceCameraPos, wp);
            float3 cell = floor(wp * 90.0);
            float h = PHash13(cell);
            float3 V = normalize(_WorldSpaceCameraPos - wp);
            float3 Hh = normalize(normalize(_UdonLightDir.xyz + 1e-4) + V);
            float facing = pow(saturate(dot(nW, Hh)), 24.0);
            float sp = step(0.992, h) * facing * mask.a * _Sparkle * (1.0 + _UdonSnow * 2.0 + snowM * 2.0);
            sp *= saturate(1.0 - dist / 7.0);
            emis += sp * sunC * 0.6;
            o.Emission = emis;
        }
        ENDCG
    }
    FallBack "Diffuse"
}
