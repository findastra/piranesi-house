// Atlas particles: 0 sparkle, 1 petal, 2 leaf, 3 snowflake. Optional ambient lighting for solid flakes.
Shader "Piranesi/Particle"
{
    Properties
    {
        _MainTex ("Atlas", 2D) = "white" {}
        _Tile ("Atlas tile (0-3)", Float) = 0
        _Color ("Color", Color) = (1,1,1,1)
        _Lit ("Lit by ambient/sun", Range(0,1)) = 0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src", Float) = 5
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst", Float) = 10
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" "PreviewType"="Plane" }
        Blend [_SrcBlend] [_DstBlend]
        ZWrite Off
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "PiranesiCommon.cginc"
            sampler2D _MainTex; float _Tile, _Lit; float4 _Color;
            struct appdata { float4 vertex : POSITION; float4 color : COLOR; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float4 color : COLOR; float2 uv : TEXCOORD0; UNITY_FOG_COORDS(1) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert (appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                float tile = floor(_Tile + 0.5);
                float2 off = float2(fmod(tile, 2.0) * 0.5, tile < 1.5 ? 0.5 : 0.0);
                o.uv = v.uv * 0.5 + off;
                float3 lightC = lerp(float3(1, 1, 1), ShadeSH9(float4(0, 1, 0, 1)) + max(_UdonSunColor.rgb, 0.0) * 0.5, _Lit);
                o.color = v.color * _Color * float4(lightC, 1);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag (v2f i) : SV_Target
            {
                fixed4 c = tex2D(_MainTex, i.uv) * i.color;
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(0, 0, 0, 0));
                return c;
            }
            ENDCG
        }
    }
}
