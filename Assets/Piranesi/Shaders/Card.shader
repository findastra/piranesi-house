// The wrist menu card: unlit, two-sided, softly self-lit so it reads at night, drawn over nearby geometry.
Shader "Piranesi/Card"
{
    Properties
    {
        _MainTex ("Card", 2D) = "white" {}
        _Fade ("Fade", Range(0, 1)) = 1
    }
    SubShader
    {
        Tags { "Queue"="Transparent+50" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off
        ZTest LEqual
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            sampler2D _MainTex; float _Fade;
            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; };
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
            v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.uv; return o; }
            fixed4 frag (v2f i, fixed facing : VFACE) : SV_Target
            {
                float2 uv = i.uv; if (facing < 0) uv.x = 1 - uv.x;      // readable from either side
                fixed4 c = tex2D(_MainTex, uv);
                return fixed4(c.rgb * 0.92, _Fade);
            }
            ENDCG
        }
    }
}
