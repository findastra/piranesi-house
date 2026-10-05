#ifndef PIRANESI_COMMON_INCLUDED
#define PIRANESI_COMMON_INCLUDED

// ---------------------------------------------------------------------------------------------
// Global state written by HouseClock (Udon) through VRCShader.SetGlobal*. Names must start with _Udon.
// ---------------------------------------------------------------------------------------------
float4 _UdonSunDir;        // direction TO the sun
float4 _UdonMoonDir;       // direction TO the moon
float4 _UdonLightDir;      // direction TO the current main light (sun by day, moon by night)
float4 _UdonSunColor;      // main light colour * intensity
float4 _UdonSkyTop;
float4 _UdonSkyHorizon;
float4 _UdonWaterShallow;
float4 _UdonWaterDeep;
float  _UdonNight;         // 0 day .. 1 night
float  _UdonSnow;          // 0..1
float  _UdonTide;          // world-space water height (m)
float  _UdonWetLine;       // highest recent water level, dries slowly
float  _UdonShaft;         // light shaft strength
float  _UdonCloud;         // cloud cover 0..1
float  _UdonReflDim;       // dims baked reflections at night

float PHash13(float3 p)
{
    p = frac(p * 0.1031);
    p += dot(p, p.zyx + 31.32);
    return frac((p.x + p.y) * p.z);
}

float PHash12(float2 p)
{
    float3 p3 = frac(float3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return frac((p3.x + p3.y) * p3.z);
}

// ---------------------------------------------------------------------------------------------
// Procedural sky: gradient, sun, moon with phase + craters, stars, drifting clouds.
// ---------------------------------------------------------------------------------------------
float3 PiranesiSky(float3 d, sampler2D noiseTex, float time)
{
    d = normalize(d);
    float h = d.y;
    float3 sunD = normalize(_UdonSunDir.xyz + float3(0, 1e-4, 0));
    float3 moonD = normalize(_UdonMoonDir.xyz + float3(0, 1e-4, 0));
    float night = _UdonNight;

    float3 top = _UdonSkyTop.rgb;
    float3 hor = _UdonSkyHorizon.rgb;
    float3 sky = lerp(hor, top, pow(saturate(h), 0.42));
    sky = lerp(sky, hor * 0.85, saturate(-h * 6.0));            // below horizon: sea haze

    // sun glow + disk
    float sd = dot(d, sunD);
    float3 sunCol = max(_UdonSunColor.rgb, 0.0);
    sky += sunCol * (pow(saturate(sd), 6.0) * 0.18 + pow(saturate(sd), 90.0) * 0.6) * (1.0 - night);
    sky += sunCol * smoothstep(0.99955, 0.99975, sd) * 30.0 * (1.0 - night) * saturate(h * 40.0 + 0.3);

    // moon
    float md = dot(d, moonD);
    if (md > 0.995)
    {
        float3 mx = normalize(cross(moonD, float3(0, 1, 0.001)));
        float3 my = cross(mx, moonD);
        float2 uv = float2(dot(d, mx), dot(d, my)) / 0.0235;
        float r2 = dot(uv, uv);
        if (r2 < 1.0)
        {
            float3 n = normalize(mx * uv.x + my * uv.y + moonD * sqrt(1.0 - r2));
            float lit = saturate(dot(n, sunD) * 0.6 + 0.62);
            float crater = tex2D(noiseTex, uv * 0.35 + 0.5).a;
            float maria = smoothstep(0.45, 0.6, tex2D(noiseTex, uv * 0.18 + 0.2).r);
            float3 mc = float3(0.95, 0.96, 1.0) * (0.75 + 0.35 * crater) * (1.0 - 0.28 * maria) * lit;
            float edge = smoothstep(1.0, 0.92, r2);
            sky = lerp(sky, mc * (1.4 + 1.2 * night), edge * saturate(h * 30.0 + 0.5));
        }
    }
    sky += float3(0.5, 0.6, 0.9) * pow(saturate(md), 400.0) * 0.6 * night;

    // stars
    if (night > 0.01 && h > 0.0)
    {
        float3 sp = d * 260.0;
        float3 cell = floor(sp);
        float rnd = PHash13(cell);
        float3 f = frac(sp) - 0.5;
        float star = step(0.9965, rnd) * smoothstep(0.25, 0.0, length(f));
        float tw = 0.6 + 0.4 * sin(time * (2.0 + rnd * 5.0) + rnd * 40.0);
        sky += star * tw * night * saturate(h * 5.0) * (1.0 - _UdonCloud) * float3(0.9, 0.95, 1.0) * 3.0;
    }

    // clouds
    if (h > 0.0)
    {
        float2 cuv = d.xz / (h + 0.12) * 0.22;
        float2 drift = float2(time * 0.0025, time * 0.0012);
        float c = tex2D(noiseTex, cuv + drift).r * 0.62 + tex2D(noiseTex, cuv * 2.7 + drift * 1.7 + 0.37).a * 0.38;
        float cover = _UdonCloud;
        float cm = smoothstep(1.0 - cover * 0.85, 1.15 - cover * 0.6, c) * saturate(h * 5.0);
        float sunSide = pow(saturate(dot(d, sunD) * 0.5 + 0.5), 3.0);
        float3 ccol = lerp(hor * 1.05, top * 0.6 + sunCol * 0.55, saturate(c * 1.2 - 0.3));
        ccol += sunCol * sunSide * 0.35 * (1.0 - night);
        ccol = lerp(ccol, float3(0.05, 0.07, 0.11) + moonD.y * 0.05, night * 0.85);
        sky = lerp(sky, ccol, cm * 0.88);
    }
    return max(sky, 0.0);
}

#endif
