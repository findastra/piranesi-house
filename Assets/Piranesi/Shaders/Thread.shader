// Ariadne's golden thread (the Thread-Bearer quest): a thin gold ribbon on the floors of the whole labyrinth. UV.x is the
// distance (m) back to the Colossus, so pulses of light run along it toward home wherever you stand.
Shader "Piranesi/Thread"
{
    Properties
    {
        _Color ("Gold", Color) = (1, 0.78, 0.35, 1)
        _Glow ("Glow", Range(0, 6)) = 1.6
        _PulseSpacing ("Metres between pulses", Float) = 9
        _PulseSpeed ("Pulse speed (m/s) toward home", Float) = 4
    }
    SubShader
    {
        Tags { "Queue"="Transparent-20" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend One One ZWrite Off Cull Off Offset -1, -1
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            float4 _Color; float _Glow, _PulseSpacing, _PulseSpeed;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; UNITY_FOG_COORDS(1) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.uv;
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float across = pow(saturate(1 - abs(i.uv.y * 2 - 1)), 0.6);
                float wave = frac(i.uv.x / _PulseSpacing + _Time.y * _PulseSpeed / _PulseSpacing);   // moves toward smaller distance: home
                float pulse = pow(1 - wave, 10) + pow(wave, 40) * 0.5;
                float3 c = _Color.rgb * _Glow * across * (0.32 + 1.6 * pulse) * lerp(1.0, 1.5, _UdonNight);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(0, 0, 0, 0));
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
