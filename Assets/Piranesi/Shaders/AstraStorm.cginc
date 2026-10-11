// Ported unchanged from findastra/astras-infinite-pole (theatre branch, Assets/Astra/Shaders/AstraStorm.cginc) for the House's Stormscape.
// Stormscape helpers (Claude, 2026-10-01). AstraStorm.cs sets these globals; with no storm both stay 0 and nothing changes.
#ifndef ASTRA_STORM_INCLUDED
#define ASTRA_STORM_INCLUDED
float _UdonStorm;   // 0 calm .. 1 full storm
float _UdonFlash;   // lightning brightness, 0 .. 1
#define STORM_HORIZON float3(.075,.072,.09)
float3 StormRainbow(float h){return .5+.5*cos(6.2832*(h+float3(0,.33,.67)));}
// storm cloud: black undersides, slate-grey tops, a dark rainbow running through the greys, lit up by lightning
float3 StormCloud(float3 world,float3 center,float up,float rim){
 float hue=dot(center,float3(.031,.023,.041))+dot(world-center,float3(.05,.08,.04))+_Time.y*.012;
 float3 rb=StormRainbow(hue);
 float3 grey=lerp(float3(.018,.018,.024),float3(.17,.17,.2),up*up);
 float3 c=grey*lerp(float3(1,1,1),rb*1.7,.4);
 c+=rb*.09*rim+float3(.05,.05,.07)*rim;
 c+=float3(.7,.76,1)*_UdonFlash*(.25+.75*up)*.6;
 return c;
}
// everything else: dim and cool it, and let lightning light it up
float3 StormDim(float3 c){return lerp(c,c*float3(.24,.25,.3)+c*float3(.5,.55,.7)*_UdonFlash,_UdonStorm);}
#endif
