#ifndef PIRANESI_SURFACE_INCLUDED
#define PIRANESI_SURFACE_INCLUDED
// Shared tide / caustics / snow helpers for UV-mapped surface shaders (props, foliage, coral).
#include "PiranesiCommon.cginc"

sampler2D _Caustics;
float _CausticStrength;

// darken + gloss below the tide / recent wet line; returns underwater factor
float PiranesiWet(float3 wp, inout float3 albedo, inout float smooth)
{
    float depthBelow = _UdonTide - wp.y;
    float under = saturate(depthBelow * 25.0);
    float wet = saturate((_UdonWetLine - wp.y) * 6.0) * (1.0 - under);
    float w = max(wet * 0.85, under);
    albedo *= lerp(1.0, 0.7, w);
    smooth = lerp(smooth, 0.9, w);
    return under;
}

float3 PiranesiCaustics(float3 wp, float3 n, float3 albedo, float under)
{
    if (under <= 0.001) return 0;
    float t = _Time.y;
    float2 cuv = wp.xz * 0.32 + wp.y * 0.05;
    float c1 = tex2D(_Caustics, cuv + float2(t * 0.031, t * 0.017)).r;
    float c2 = tex2D(_Caustics, cuv * 1.37 + float2(-t * 0.022, t * 0.029)).r;
    float depth = max(_UdonTide - wp.y, 0.0);
    return min(c1, c2) * 3.0 * under * max(_UdonSunColor.rgb, 0.0) * _CausticStrength * exp(-depth * 0.45)
           * saturate(n.y * 0.7 + 0.3) * albedo;
}

// depth tint for things deep under water (colour shifts to blue-green)
float3 PiranesiUnderwaterTint(float3 wp, float3 col)
{
    float depth = max(_UdonTide - wp.y, 0.0);
    float3 absorb = exp(-depth * float3(0.30, 0.06, 0.05));
    return col * lerp(1.0, absorb, saturate(depth * 4.0));
}
#endif
