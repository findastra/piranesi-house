// The sea that fills the House. Gerstner swell outside (calm inside the halls), refraction,
// depth absorption (turquoise shallows), box-projected reflections, sun glitter, shore foam.
Shader "Piranesi/Ocean"
{
    Properties
    {
        [Normal] _Normal0 ("Detail normal A", 2D) = "bump" {}
        [Normal] _Normal1 ("Detail normal B", 2D) = "bump" {}
        _NoiseTex ("Noise", 2D) = "gray" {}
        _Tile0 ("Normal A tile (m)", Float) = 9
        _Tile1 ("Normal B tile (m)", Float) = 23
        _DetailStrength ("Detail normal strength", Range(0,2)) = 0.55
        _InsideDetail ("Detail strength inside halls", Range(0,2)) = 0.18
        _Absorption ("Absorption (per m)", Vector) = (0.42, 0.075, 0.06, 0)
        _Scatter ("Scatter strength", Range(0,2)) = 0.55
        _Refraction ("Refraction", Range(0,0.2)) = 0.045
        _FoamDist ("Shore foam distance", Float) = 0.35
        _WaveA ("Wave A (dir.xy, steepness, wavelength)", Vector) = (1, 0.3, 0.16, 38)
        _WaveB ("Wave B", Vector) = (0.7, 0.8, 0.13, 21)
        _WaveC ("Wave C", Vector) = (-0.3, 1, 0.1, 13)
        _WaveD ("Wave D", Vector) = (0.9, -0.4, 0.08, 7.5)
        _HouseHalf ("House half size (m)", Float) = 73
        _InsideAmp ("Wave amplitude inside", Range(0,1)) = 0.04
    }
    SubShader
    {
        Tags { "Queue"="Geometry+400" "RenderType"="Opaque" "IgnoreProjector"="True" "DisableBatching"="True" }
        GrabPass { "_PiranesiWaterGrab" }
        Pass
        {
            Tags { "LightMode"="ForwardBase" }
            Cull Off
            ZWrite On
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_fwdbase
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            #include "AutoLight.cginc"
            #include "UnityStandardUtils.cginc"
            #include "PiranesiCommon.cginc"

            sampler2D _Normal0, _Normal1, _NoiseTex;
            UNITY_DECLARE_SCREENSPACE_TEXTURE(_PiranesiWaterGrab);
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);
            float _Tile0, _Tile1, _DetailStrength, _InsideDetail, _Scatter, _Refraction, _FoamDist, _HouseHalf, _InsideAmp;
            float4 _Absorption, _WaveA, _WaveB, _WaveC, _WaveD;

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wp : TEXCOORD0;
                float3 nrm : TEXCOORD1;
                float4 screenPos : TEXCOORD2;
                float4 grabPos : TEXCOORD3;
                float inside : TEXCOORD4;
                UNITY_FOG_COORDS(5)
                SHADOW_COORDS(6)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            float3 Gerstner(float4 w, float3 p, float amp, inout float3 tangent, inout float3 binormal)
            {
                float steep = w.z * amp;
                float k = 2.0 * UNITY_PI / w.w;
                float c = sqrt(9.8 / k);
                float2 d = normalize(w.xy);
                float f = k * (dot(d, p.xz) - c * _Time.y);
                float a = steep / k;
                tangent += float3(-d.x * d.x * (steep * sin(f)), d.x * (steep * cos(f)), -d.x * d.y * (steep * sin(f)));
                binormal += float3(-d.x * d.y * (steep * sin(f)), d.y * (steep * cos(f)), -d.y * d.y * (steep * sin(f)));
                return float3(d.x * (a * cos(f)), a * sin(f), d.y * (a * cos(f)));
            }

            v2f vert (appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                float edge = max(abs(wp.x), abs(wp.z));
                float inside = 1.0 - saturate((edge - _HouseHalf) / 25.0);
                float far = saturate((length(wp.xz) - 600.0) / 900.0);
                float amp = lerp(1.0, _InsideAmp, inside) * (1.0 - far);
                float3 t = float3(1, 0, 0), b = float3(0, 0, 1);
                float3 g = 0;
                g += Gerstner(_WaveA, wp, amp, t, b);
                g += Gerstner(_WaveB, wp, amp, t, b);
                g += Gerstner(_WaveC, wp, amp, t, b);
                g += Gerstner(_WaveD, wp, amp, t, b);
                wp += g;
                o.wp = wp;
                o.nrm = normalize(cross(b, t));
                o.inside = inside;
                o.pos = mul(UNITY_MATRIX_VP, float4(wp, 1));
                o.screenPos = ComputeScreenPos(o.pos);
                o.grabPos = ComputeGrabScreenPos(o.pos);
                UNITY_TRANSFER_FOG(o, o.pos);
                TRANSFER_SHADOW(o);
                return o;
            }

            fixed4 frag (v2f i, fixed facing : VFACE) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 wp = i.wp;
                float3 V = normalize(_WorldSpaceCameraPos - wp);
                float t = _Time.y;

                // detail normals
                float2 uv0 = wp.xz / _Tile0 + float2(t * 0.021, t * 0.012);
                float2 uv1 = wp.xz / _Tile1 + float2(-t * 0.009, t * 0.017);
                float3 n0 = UnpackNormal(tex2D(_Normal0, uv0));
                float3 n1 = UnpackNormal(tex2D(_Normal1, uv1));
                float2 dn = (n0.xy + n1.xy) * lerp(_DetailStrength, _InsideDetail, i.inside);
                float3 N = normalize(i.nrm + float3(dn.x, 0, dn.y));
                if (facing < 0) N = -N;

                // depth & refraction
                float surfZ = i.screenPos.w;
                float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.screenPos)));
                float thick = max(0.0, sceneZ - surfZ);
                float2 offs = N.xz * _Refraction * saturate(thick * 0.8);
                float4 sp2 = i.screenPos; sp2.xy += offs * sp2.w;
                float sceneZ2 = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(sp2)));
                float4 gp = i.grabPos;
                if (sceneZ2 > surfZ) { gp.xy += offs * gp.w; thick = sceneZ2 - surfZ; }
                float3 refr = UNITY_SAMPLE_SCREENSPACE_TEXTURE(_PiranesiWaterGrab, gp.xy / gp.w).rgb;

                // absorption + in-scatter (turquoise shallows, deep blue far)
                float path = thick;
                float3 trans = exp(-path * _Absorption.rgb);
                float3 lightC = max(_UdonSunColor.rgb, 0.0);
                float3 amb = ShadeSH9(float4(0, 1, 0, 1));
                float3 scatterCol = lerp(_UdonWaterDeep.rgb, _UdonWaterShallow.rgb, exp(-path * 0.12));
                float3 inscatter = scatterCol * (amb * 0.9 + lightC * 0.45) * _Scatter;
                float3 col = refr * trans + inscatter * (1.0 - trans);

                // reflection (box projected probe), dimmed at night
                float3 R = reflect(-V, N);
                float3 Rp = R;
                #if UNITY_SPECCUBE_BOX_PROJECTION
                    Rp = BoxProjectedCubemapDirection(R, wp, unity_SpecCube0_ProbePosition, unity_SpecCube0_BoxMin, unity_SpecCube0_BoxMax);
                #endif
                float3 refl = DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0, Rp, 0.5), unity_SpecCube0_HDR);
                float rd = (_UdonReflDim > 0.001 ? _UdonReflDim : 1.0);
                refl *= rd;
                float NdV = saturate(dot(N, V));
                float fres = 0.02 + 0.98 * pow(1.0 - NdV, 5.0);
                col = lerp(col, refl, saturate(fres * 1.1));

                // sun / moon specular + glitter
                float shadow = SHADOW_ATTENUATION(i);
                float3 L = normalize(_WorldSpaceLightPos0.xyz);
                float3 H = normalize(L + V);
                float NdH = saturate(dot(N, H));
                // specular AA: widen the highlight where the normal changes fast across pixels
                float3 dnx = ddx(N), dny = ddy(N);
                float nvar = saturate(0.5 * (dot(dnx, dnx) + dot(dny, dny)) * 40.0);
                float p1 = lerp(900.0, 140.0, nvar);
                float spec = pow(NdH, p1) * lerp(14.0, 3.0, nvar) + pow(NdH, 120.0) * 0.4;
                float2 gcell = floor(wp.xz * 12.0 + float2(t * 0.6, -t * 0.45));
                float gl = step(0.996, PHash12(gcell)) * pow(NdH, 60.0) * 3.0 * (1.0 - nvar) * saturate(1.0 - distance(_WorldSpaceCameraPos, wp) / 35.0);
                col += (spec + gl) * _LightColor0.rgb * shadow;

                // shore / intersection foam
                float fn = tex2D(_NoiseTex, wp.xz * 0.35 + t * 0.03).r;
                float foam = saturate(1.0 - thick / _FoamDist) * smoothstep(0.35, 0.65, fn + 0.25);
                float crest = saturate((wp.y - _UdonTide - 0.45) * 2.0) * (1.0 - i.inside) * smoothstep(0.5, 0.8, fn);
                col = lerp(col, (amb + lightC * shadow) * 0.9, saturate(foam * 0.75 + crest * 0.6));

                UNITY_APPLY_FOG(i.fogCoord, col);
                return fixed4(col, 1);
            }
            ENDCG
        }
    }
    FallBack Off
}
