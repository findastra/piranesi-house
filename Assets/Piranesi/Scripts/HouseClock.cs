using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// The House's clock. Every client derives day/night, season and tide from the shared server time,
/// so the whole instance sees the same sky and the same water without any network sync.
/// Drives: sun/moon light, sky + fog + ambient palettes, water colours, tide height, snow,
/// light-shaft strength, lantern brightness, seasonal particles and wind volume.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseClock : UdonSharpBehaviour
{
    [Header("Cycle lengths (seconds)")]
    public float dayLength = 720f;
    [Range(0.3f, 0.9f)] public float dayFraction = 0.64f;
    public float seasonLength = 360f;
    public float tideLength = 420f;
    public float tideLow = -0.45f;
    public float tideHigh = 0.85f;
    [Tooltip("Shifts the clock so a fresh instance doesn't always start at the same moment")]
    public float timeOffset = 180f;

    [Header("Scene references")]
    public Light mainLight;
    public Transform water;
    public Light[] lanterns;
    public float lanternBase = 1.3f;
    public ParticleSystem[] spring;
    public ParticleSystem[] summer;
    public ParticleSystem[] autumn;
    public ParticleSystem[] winter;
    public AudioSource[] windSources;
    public AudioSource shimmer;
    public HouseFootsteps footsteps;
    public HouseBoat[] boats;
    public HouseDolphins dolphins;

    [Header("Season palettes (0 spring, 1 summer, 2 autumn, 3 winter)")]
    public Color[] skyTop;
    public Color[] skyHorizon;
    public Color[] sunColor;
    public Color[] fogColor;
    public Color[] waterShallow;
    public Color[] waterDeep;
    public Color[] ambientSky;
    public Color[] ambientEquator;
    public Color[] ambientGround;
    public float[] fogDensity;
    public float[] sunMaxElevation;
    public float[] cloudCover;
    public float[] windVolume;

    [Header("Night")]
    public Color nightSkyTop = new Color(0.01f, 0.02f, 0.05f);
    public Color nightSkyHorizon = new Color(0.05f, 0.08f, 0.14f);
    public Color moonColor = new Color(0.55f, 0.65f, 0.9f);
    public Color sunsetColor = new Color(1.0f, 0.5f, 0.28f);
    public Color nightFog = new Color(0.04f, 0.07f, 0.11f);
    public Color nightWaterShallow = new Color(0.05f, 0.18f, 0.24f);
    public Color nightWaterDeep = new Color(0.01f, 0.03f, 0.07f);
    public Color nightAmbientSky = new Color(0.06f, 0.09f, 0.16f);
    public Color nightAmbientEquator = new Color(0.04f, 0.06f, 0.1f);
    public Color nightAmbientGround = new Color(0.02f, 0.03f, 0.05f);
    public float nightFogDensity = 0.006f;
    public float sunIntensity = 1.35f;
    public float moonIntensity = 0.32f;

    // shader property ids (VRCShader requires the _Udon prefix)
    private int idSunDir, idMoonDir, idLightDir, idSunColor, idSkyTop, idSkyHorizon, idWaterShallow, idWaterDeep;
    private int idNight, idSnow, idTide, idWetLine, idShaft, idCloud, idReflDim;
    private bool idsReady;

    private float snow;
    private float wetLine = -10f;
    private int lastSeason = -1;
    private float slowTimer;
    private float lastTide;

    void Start()
    {
        InitIds();
        wetLine = tideLow;
    }

    public void InitIds()
    {
        idSunDir = VRCShader.PropertyToID("_UdonSunDir");
        idMoonDir = VRCShader.PropertyToID("_UdonMoonDir");
        idLightDir = VRCShader.PropertyToID("_UdonLightDir");
        idSunColor = VRCShader.PropertyToID("_UdonSunColor");
        idSkyTop = VRCShader.PropertyToID("_UdonSkyTop");
        idSkyHorizon = VRCShader.PropertyToID("_UdonSkyHorizon");
        idWaterShallow = VRCShader.PropertyToID("_UdonWaterShallow");
        idWaterDeep = VRCShader.PropertyToID("_UdonWaterDeep");
        idNight = VRCShader.PropertyToID("_UdonNight");
        idSnow = VRCShader.PropertyToID("_UdonSnow");
        idTide = VRCShader.PropertyToID("_UdonTide");
        idWetLine = VRCShader.PropertyToID("_UdonWetLine");
        idShaft = VRCShader.PropertyToID("_UdonShaft");
        idCloud = VRCShader.PropertyToID("_UdonCloud");
        idReflDim = VRCShader.PropertyToID("_UdonReflDim");
        idsReady = true;
    }

    void Update()
    {
        double t = Networking.GetServerTimeInSeconds() + timeOffset;
        float day = (float)((t / dayLength) % 1.0);
        float season = (float)((t / seasonLength) % 4.0);
        float tidePhase = (float)((t / tideLength) % 1.0);
        float tide = Mathf.Lerp(tideLow, tideHigh, 0.5f - 0.5f * Mathf.Cos(tidePhase * 2f * Mathf.PI));

        float winterW = WinterWeight(season);
        snow = Mathf.MoveTowards(snow, winterW, Time.deltaTime / 75f);
        wetLine = Mathf.Max(tide, wetLine - Time.deltaTime * 0.0025f);

        slowTimer -= Time.deltaTime;
        bool slow = slowTimer <= 0f;
        if (slow) slowTimer = 0.5f;
        ApplyState(day, season, tide, snow, wetLine, slow);
    }

    public float WinterWeight(float season)
    {
        int idx = (int)Mathf.Floor(season) % 4;
        float f = season - Mathf.Floor(season);
        float b = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.8f, 1f, f));
        if (idx == 3) return 1f - b;
        if (idx == 2) return b;
        return 0f;
    }

    private Color Pal(Color[] pal, int idx, float b)
    {
        return Color.Lerp(pal[idx], pal[(idx + 1) % 4], b);
    }

    private float PalF(float[] pal, int idx, float b)
    {
        return Mathf.Lerp(pal[idx], pal[(idx + 1) % 4], b);
    }

    private Vector3 DirFrom(float elevDeg, float azDeg)
    {
        float e = elevDeg * Mathf.Deg2Rad;
        float a = azDeg * Mathf.Deg2Rad;
        return new Vector3(Mathf.Sin(a) * Mathf.Cos(e), Mathf.Sin(e), Mathf.Cos(a) * Mathf.Cos(e));
    }

    /// <summary>Apply a full visual state. Also callable from the editor preview window.</summary>
    public void ApplyState(float day, float season, float tide, float snowAmount, float wet, bool slowUpdate)
    {
        if (!idsReady) InitIds();
        int idx = (int)Mathf.Floor(season) % 4;
        float f = season - Mathf.Floor(season);
        float b = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.8f, 1f, f));

        // ---- sun & moon
        float maxElev = PalF(sunMaxElevation, idx, b);
        Vector3 sunDir;
        Vector3 moonDir;
        if (day < dayFraction)
        {
            float p = day / dayFraction;
            sunDir = DirFrom(Mathf.Sin(p * Mathf.PI) * maxElev - 4f, Mathf.Lerp(80f, 280f, p));
            moonDir = DirFrom(-Mathf.Sin(p * Mathf.PI) * 30f - 5f, Mathf.Lerp(260f, 440f, p));
        }
        else
        {
            float n = (day - dayFraction) / (1f - dayFraction);
            sunDir = DirFrom(-Mathf.Sin(n * Mathf.PI) * 35f - 4f, Mathf.Lerp(280f, 440f, n));
            moonDir = DirFrom(Mathf.Sin(n * Mathf.PI) * 58f - 2f, Mathf.Lerp(100f, 250f, n));
        }
        float night = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.06f, -0.1f, sunDir.y));
        float twilight = Mathf.Clamp01(1f - Mathf.Abs(sunDir.y) / 0.28f) * (1f - night * 0.6f);

        Color sunC = Color.Lerp(Pal(sunColor, idx, b), sunsetColor, twilight * 0.85f);
        float sunUp = Mathf.Clamp01(sunDir.y * 4f + 0.15f);
        float moonUp = Mathf.Clamp01(moonDir.y * 3f);
        Vector3 lightDir = night < 0.5f ? sunDir : moonDir;
        Color lightC = night < 0.5f ? sunC * (sunIntensity * sunUp) : moonColor * (moonIntensity * moonUp);

        if (mainLight != null)
        {
            mainLight.transform.rotation = Quaternion.LookRotation(-lightDir);
            mainLight.color = lightC;
            mainLight.intensity = 1f;
            mainLight.shadowStrength = Mathf.Lerp(0.85f, 0.6f, night);
        }

        // ---- sky / fog / ambient
        Color top = Color.Lerp(Pal(skyTop, idx, b), nightSkyTop, night);
        Color hor = Color.Lerp(Color.Lerp(Pal(skyHorizon, idx, b), sunsetColor, twilight * 0.55f), nightSkyHorizon, night);
        Color fog = Color.Lerp(Color.Lerp(Pal(fogColor, idx, b), sunsetColor * 0.6f, twilight * 0.3f), nightFog, night);
        RenderSettings.fogColor = fog;
        RenderSettings.fogDensity = Mathf.Lerp(PalF(fogDensity, idx, b), nightFogDensity, night);
        RenderSettings.ambientSkyColor = Color.Lerp(Pal(ambientSky, idx, b), nightAmbientSky, night);
        RenderSettings.ambientEquatorColor = Color.Lerp(Pal(ambientEquator, idx, b), nightAmbientEquator, night);
        RenderSettings.ambientGroundColor = Color.Lerp(Pal(ambientGround, idx, b), nightAmbientGround, night);

        float cloud = PalF(cloudCover, idx, b);

        VRCShader.SetGlobalVector(idSunDir, new Vector4(sunDir.x, sunDir.y, sunDir.z, 0f));
        VRCShader.SetGlobalVector(idMoonDir, new Vector4(moonDir.x, moonDir.y, moonDir.z, 0f));
        VRCShader.SetGlobalVector(idLightDir, new Vector4(lightDir.x, lightDir.y, lightDir.z, 0f));
        VRCShader.SetGlobalColor(idSunColor, lightC);
        VRCShader.SetGlobalColor(idSkyTop, top);
        VRCShader.SetGlobalColor(idSkyHorizon, hor);
        VRCShader.SetGlobalColor(idWaterShallow, Color.Lerp(Pal(waterShallow, idx, b), nightWaterShallow, night));
        VRCShader.SetGlobalColor(idWaterDeep, Color.Lerp(Pal(waterDeep, idx, b), nightWaterDeep, night));
        VRCShader.SetGlobalFloat(idNight, night);
        VRCShader.SetGlobalFloat(idSnow, snowAmount);
        VRCShader.SetGlobalFloat(idTide, tide);
        VRCShader.SetGlobalFloat(idWetLine, wet);
        VRCShader.SetGlobalFloat(idShaft, (1f - night) * sunUp * (1f - cloud * 0.55f) + night * moonUp * 0.35f);
        VRCShader.SetGlobalFloat(idCloud, cloud);
        VRCShader.SetGlobalFloat(idReflDim, Mathf.Lerp(1f, 0.22f, night));

        if (footsteps != null) footsteps.SetTide(tide);
        if (boats != null)
            for (int bi = 0; bi < boats.Length; bi++) if (boats[bi] != null) boats[bi].SetTide(tide);
        if (dolphins != null) dolphins.SetTide(tide);
        if (water != null)
        {
            Vector3 wp = water.position;
            wp.y = tide;
            water.position = wp;
        }

        if (!slowUpdate) return;

        // ---- lanterns burn brighter at night
        if (lanterns != null)
        {
            float li = lanternBase * Mathf.Lerp(0.75f, 1.7f, night);
            for (int i = 0; i < lanterns.Length; i++)
            {
                if (lanterns[i] != null) lanterns[i].intensity = li;
            }
        }

        // ---- seasonal particles + wind
        int active = b < 0.5f ? idx : (idx + 1) % 4;
        SetSystems(spring, active == 0);
        SetSystems(summer, active == 1);
        SetSystems(autumn, active == 2);
        SetSystems(winter, active == 3);
        if (windSources != null && windVolume != null && windVolume.Length == 4)
        {
            float wv = PalF(windVolume, idx, b);
            for (int i = 0; i < windSources.Length; i++)
            {
                if (windSources[i] != null) windSources[i].volume = wv;
            }
        }
        if (lastSeason != -1 && lastSeason != active && shimmer != null) shimmer.Play();
        lastSeason = active;
    }

    private void SetSystems(ParticleSystem[] systems, bool on)
    {
        if (systems == null) return;
        for (int i = 0; i < systems.Length; i++)
        {
            ParticleSystem ps = systems[i];
            if (ps == null) continue;
            if (on && !ps.isPlaying) ps.Play();
            else if (!on && ps.isPlaying) ps.Stop();
        }
    }
}
