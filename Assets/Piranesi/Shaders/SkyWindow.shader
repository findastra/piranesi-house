// Window glass that shows the live sky in the viewing direction (reads as an opening to the outside).
Shader "Piranesi/SkyWindow"
{
    Properties { _NoiseTex ("Noise", 2D) = "gray" {} _Brightness ("Brightness", Float) = 1.6 _Frost ("Frost", Range(0,1)) = 0.25 }
    SubShader
    {
        Tags { "Queue"="Geometry" "RenderType"="Opaque" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            sampler2D _NoiseTex; float _Brightness, _Frost;
            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 wp : TEXCOORD0; UNITY_FOG_COORDS(1) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                float3 d = normalize(i.wp - _WorldSpaceCameraPos);
                d.y = abs(d.y) * 0.6 + 0.25;
                float3 c = PiranesiSky(d, _NoiseTex, _Time.y) * _Brightness;
                float fr = tex2D(_NoiseTex, i.wp.xz * 0.7 + i.wp.y * 0.3).b;
                c = lerp(c, dot(c, float3(0.33, 0.34, 0.33)) * float3(0.95, 0.97, 1.0) * 1.1, _Frost * (0.6 + 0.4 * fr));
                UNITY_APPLY_FOG(i.fogCoord, c);
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
