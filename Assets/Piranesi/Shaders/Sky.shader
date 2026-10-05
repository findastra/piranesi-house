// Procedural sky driven by HouseClock: season palettes, sun, moon, stars, clouds.
Shader "Piranesi/Sky"
{
    Properties { _NoiseTex ("Noise", 2D) = "gray" {} _Exposure ("Exposure", Float) = 1 }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" }
        Cull Off ZWrite Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            sampler2D _NoiseTex; float _Exposure;
            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.dir = v.vertex.xyz;
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                return fixed4(PiranesiSky(i.dir, _NoiseTex, _Time.y) * _Exposure, 1);
            }
            ENDCG
        }
    }
    FallBack Off
}
