using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRC.SDK3.Persistence;

/// <summary>
/// v3 the dead-end easter egg and the Stormscape, for each player on their own (nothing here is synced).
///   Found(i)      a dead end walked into: a chime, the court figure glitters, the plaque at the camp turns (0 / 5 .. 5 / 5).
///                 The count is saved to the player (PlayerData) and comes back next visit.
///   BeginStorm()  at 5 / 5, or from the secret rosette under the Colossus' foot: the sky goes black, rain, lightning and
///                 thunder (Astra's Stormscape globals _UdonStorm / _UdonFlash), the dome opens, the Climb vine goes, and
///                 Astra's Infinite Pole rises out of the palm with the Infinite Spiral round it. The spiral's turns are
///                 recycled round the player, so the stair is as long as you like, up to the landing at the top.
///                 Climbing: storm, then a whiteout, then stars (HouseClock blends the sky, fog and light).
///   BeginEndShow() stepping into Astra's phone booth on the landing: a meteor shower, then the hyperspace dive (star
///                 streaks and a tunnel of the six road colours, falling back down through the oculus into the palm),
///                 a blackout, and you wake at the spawn camp with the storm gone.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseStorm : UdonSharpBehaviour
{
    [Header("Dead ends (0 / 5)")]
    public GameObject[] tally;                 // the plaques 0/5 .. 5/5 on the spawn stand (one shown)
    public ParticleSystem[] bursts;            // glitter at each court figure
    public AudioSource chime;
    public float stormDelay = 3f;

    [Header("Storm")]
    public HouseClock clock;
    public Material stormSky;
    public Material starsSky;
    public Transform follower;                 // rain, the rain sound and the meteors follow the player
    public ParticleSystem rain;
    public AudioSource rainSound;
    public GameObject[] bolts;
    public AudioSource thunder;
    public AudioClip[] thunderClips;
    public float fadeSeconds = 4f, boltEvery = 6.5f;
    public GameObject[] domeClosed;
    public GameObject[] domeOpen;
    public GameObject[] hideInStorm;

    [Header("Astra's Infinite Pole and the Infinite Spiral")]
    public GameObject stair;                   // pole, turns, landing, booth (off until the storm)
    public Transform pole;
    public Transform[] turns;
    public float baseY = 13.8f, pitch = 6.4f;
    public int topTurns = 55;
    public float grow = 12f, growDelay = 5f, growHeight = 120f;
    public float white0 = 40f, white1 = 120f, stars0 = 200f, stars1 = 300f;

    [Header("End Show")]
    public ParticleSystem meteors;
    public AudioSource meteorSound;
    public float meteorSeconds = 12f;
    public VRCStation diveStation;
    public Transform diveSeat;
    public Transform booth;
    public Vector3 palm = new Vector3(0f, 14.2f, 0f);
    public float diveSeconds = 9f;
    public Transform warp;
    public Material warpMat;
    public AudioSource warpSound;
    public Transform blackout;
    public Material blackoutMat;
    public float fadeIn = 0.6f, hold = 2.2f, fadeOut = 1.8f;
    public Transform spawnPoint;

    private const string Key = "piranesi.deadends";
    private int found;                         // bit mask of the five dead ends
    private int phase;                         // 0 calm, 1 storm, 2 meteors, 3 dive, 4 blackout
    private float level, phaseStart, stormStart;
    private bool raining, stairShown, domeIsOpen, homed;
    private Material savedSky;
    private int stormId, flashId, lastSlot = -1, lastCenter = int.MinValue, thunderSlot;
    private float thunderAt = -1f;
    private Vector3 diveFrom;
    private VRCPlayerApi player;

    void Start()
    {
        player = Networking.LocalPlayer;
        stormId = VRCShader.PropertyToID("_UdonStorm");
        flashId = VRCShader.PropertyToID("_UdonFlash");
        VRCShader.SetGlobalFloat(stormId, 0f);
        VRCShader.SetGlobalFloat(flashId, 0f);
        if (rain != null) rain.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        SetAll(bolts, false);
        if (stair != null) stair.SetActive(false);
        SetAll(domeOpen, false);
        if (warp != null) warp.gameObject.SetActive(false);
        if (blackout != null) blackout.gameObject.SetActive(false);
        ShowTally();
    }

    // ------------------------------------------------------------------ the dead ends
    public override void OnPlayerRestored(VRCPlayerApi p)
    {
        if (!Utilities.IsValid(p) || !p.isLocal) return;
        int v;
        if (PlayerData.TryGetInt(p, Key, out v)) found = v & 31;
        ShowTally();
    }

    public void Found(int i)
    {
        if (i < 0 || i > 4) return;
        int bit = 1 << i;
        if ((found & bit) != 0) return;
        found |= bit;
        PlayerData.SetInt(Key, found);
        if (chime != null) chime.Play();
        if (bursts != null && i < bursts.Length && bursts[i] != null) bursts[i].Play();
        ShowTally();
        if (Count() == 5 && phase == 0) SendCustomEventDelayedSeconds(nameof(BeginStorm), stormDelay);
    }

    public int Count()
    {
        int n = 0;
        for (int i = 0; i < 5; i++) if ((found & (1 << i)) != 0) n++;
        return n;
    }

    private void ShowTally()
    {
        if (tally == null) return;
        int n = Count();
        for (int i = 0; i < tally.Length; i++) if (tally[i] != null) tally[i].SetActive(i == n);
    }

    // ------------------------------------------------------------------ the storm
    public void BeginStorm()
    {
        if (phase != 0) return;
        phase = 1; stormStart = Time.time; stairShown = false; domeIsOpen = false; homed = false; lastCenter = int.MinValue;
    }

    private void OpenDome(bool open)
    {
        domeIsOpen = open;
        SetAll(domeClosed, !open);
        SetAll(domeOpen, open);
        SetAll(hideInStorm, !open);
    }

    void Update()
    {
        if (phase == 0 && level <= 0f) return;
        if (!Utilities.IsValid(player)) { player = Networking.LocalPlayer; return; }
        Vector3 pp = player.GetPosition();
        float now = Time.time;

        // storm level: up while the storm runs, down when it is over
        float target = phase >= 1 && !homed ? 1f : 0f;
        float prev = level;
        level = Mathf.MoveTowards(level, target, Time.deltaTime / Mathf.Max(0.1f, fadeSeconds));
        if (prev <= 0f && level > 0f && RenderSettings.skybox != stormSky && RenderSettings.skybox != starsSky) savedSky = RenderSettings.skybox;
        if (follower != null) follower.position = pp;

        // the stair: after a pause the dome opens and the pole rises, the turns appearing from the palm upward
        float rise = 0f;
        if (phase >= 1 && !homed)
        {
            float t = now - stormStart - growDelay;
            if (t >= 0f && !domeIsOpen) OpenDome(true);
            if (t >= 0f && !stairShown) { stairShown = true; if (stair != null) stair.SetActive(true); }
            rise = Mathf.Clamp01(t / Mathf.Max(0.1f, grow));
            if (pole != null) pole.localScale = new Vector3(1f, Mathf.Max(0.001f, rise), 1f);
        }
        if (stairShown && !homed) PlaceTurns(pp.y, rise);

        // how high you are on the stair: storm, then whiteout, then stars
        float above = pp.y - baseY;
        float w = phase >= 1 && !homed ? Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(white0, white1, above)) : 0f;
        float s = phase >= 1 && !homed ? Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(stars0, stars1, above)) : 0f;

        // sky
        Material want = savedSky;
        if (level > 0.5f) want = s > 0.5f ? starsSky : (w > 0.5f ? savedSky : stormSky);
        if (want != null && RenderSettings.skybox != want) RenderSettings.skybox = want;

        // rain and its sound
        float wet = level * (1f - w);
        bool rainWant = wet > 0.25f;
        if (rain != null)
        {
            if (rainWant && !raining) { rain.Play(); raining = true; }
            else if (!rainWant && raining) { rain.Stop(true, ParticleSystemStopBehavior.StopEmitting); raining = false; }
        }
        if (rainSound != null)
        {
            if (wet > 0.01f && !rainSound.isPlaying) rainSound.Play();
            rainSound.volume = 0.7f * wet;
            if (wet <= 0.01f && rainSound.isPlaying) rainSound.Stop();
        }

        // lightning (this player's own storm: local time), thunder a moment later
        float flash = 0f;
        if (level > 0.8f && w < 0.4f)
        {
            int slot = (int)(now / boltEvery);
            float strikeAt = slot * boltEvery + Hash(slot) * (boltEvery - 1.2f);
            float since = now - strikeAt;
            int which = bolts != null && bolts.Length > 0 ? Mathf.Clamp((int)(Hash(slot + 17.3f) * bolts.Length), 0, bolts.Length - 1) : -1;
            if (since >= 0f && since < 0.7f)
            {
                flash = since < 0.08f ? 1f : since < 0.16f ? 0.25f : since < 0.26f ? 0.85f : Mathf.Max(0f, 0.6f * (1f - (since - 0.26f) / 0.44f));
                if (lastSlot != slot)
                {
                    lastSlot = slot;
                    if (bolts != null) for (int i = 0; i < bolts.Length; i++) if (bolts[i] != null) bolts[i].SetActive(i == which);
                    thunderSlot = slot; thunderAt = now + 0.6f + Hash(slot + 5.1f) * 1.6f;
                }
            }
            else if (since >= 0.7f) SetAll(bolts, false);
            if (thunderAt > 0f && now >= thunderAt)
            {
                thunderAt = -1f;
                if (thunder != null && thunderClips != null && thunderClips.Length > 0)
                {
                    thunder.volume = 0.6f * level;
                    thunder.PlayOneShot(thunderClips[thunderSlot % thunderClips.Length]);
                }
            }
        }
        else SetAll(bolts, false);
        flash *= level * (1f - w);

        VRCShader.SetGlobalFloat(stormId, level * (1f - w));
        VRCShader.SetGlobalFloat(flashId, flash);
        if (clock != null) { clock.storm = level; clock.white = w * level; clock.starsW = s * level; clock.flash = flash; }

        // the End Show
        if (phase == 2 && now - phaseStart >= meteorSeconds) StartDive();
        if (phase == 3) Dive(now);
        if (phase == 4) Blackout(now);

        if (phase == 0 && level <= 0f) Calm();
    }

    private void PlaceTurns(float y, float rise)
    {
        if (turns == null || turns.Length == 0) return;
        int n = turns.Length;
        int center = Mathf.FloorToInt((y - baseY) / pitch);
        int top = rise >= 1f ? topTurns - 1 : Mathf.FloorToInt(rise * growHeight / pitch);
        int half = (n - 1) / 2;
        for (int i = center - half; i <= center + half; i++)
        {
            int slot = ((i % n) + n) % n;
            Transform tr = turns[slot];
            if (tr == null) continue;
            bool show = i >= 0 && i < topTurns && i <= top;
            if (tr.gameObject.activeSelf != show) tr.gameObject.SetActive(show);
            if (show) tr.localPosition = new Vector3(0f, baseY + i * pitch, 0f);
        }
        lastCenter = center;
    }

    // ------------------------------------------------------------------ the End Show
    public void BeginEndShow()
    {
        if (phase != 1) return;
        phase = 2; phaseStart = Time.time;
        if (meteors != null) meteors.Play();
        if (meteorSound != null) meteorSound.Play();
    }

    private void StartDive()
    {
        phase = 3; phaseStart = Time.time;
        if (meteors != null) meteors.Stop(true, ParticleSystemStopBehavior.StopEmitting);
        diveFrom = booth != null ? booth.position + Vector3.up * 0.2f : player.GetPosition();
        if (diveSeat != null) diveSeat.position = diveFrom;
        if (diveStation != null) diveStation.UseStation(player);
        if (warp != null) warp.gameObject.SetActive(true);
        if (warpSound != null) warpSound.Play();
    }

    private void Dive(float now)
    {
        float t = Mathf.Clamp01((now - phaseStart) / Mathf.Max(0.1f, diveSeconds));
        // swing in to the axis over the first fifth, then fall straight down through the oculus, slowing into the palm
        Vector3 above = new Vector3(palm.x, diveFrom.y, palm.z);
        Vector3 p;
        if (t < 0.2f) p = Vector3.Lerp(diveFrom, above, Mathf.SmoothStep(0f, 1f, t / 0.2f));
        else
        {
            float f = (t - 0.2f) / 0.8f;
            float e = f < 0.85f ? Mathf.Pow(f / 0.85f, 1.6f) * 0.97f : 0.97f + 0.03f * Mathf.SmoothStep(0f, 1f, (f - 0.85f) / 0.15f);
            p = Vector3.Lerp(above, palm, e);
        }
        if (diveSeat != null) diveSeat.position = p;
        if (warp != null) warp.position = p;
        float amount = Mathf.Clamp01(t / 0.15f) * Mathf.Clamp01((1f - t) / 0.12f);
        if (warpMat != null) { warpMat.SetFloat("_Amount", amount); warpMat.SetFloat("_Rush", 0.8f + 2.6f * Mathf.Sin(t * Mathf.PI)); }
        if (warpSound != null) warpSound.volume = 0.9f * amount;
        if (t >= 1f) { phase = 4; phaseStart = now; if (blackout != null) blackout.gameObject.SetActive(true); }
    }

    private void Blackout(float now)
    {
        float t = now - phaseStart;
        float a;
        if (t < fadeIn) a = t / fadeIn;
        else if (t < fadeIn + hold)
        {
            a = 1f;
            if (!homed) Home();                                     // in the dark: put the world back and wake at the camp
        }
        else a = 1f - Mathf.Clamp01((t - fadeIn - hold) / Mathf.Max(0.1f, fadeOut));
        if (blackoutMat != null) blackoutMat.SetFloat("_Alpha", Mathf.Clamp01(a));
        if (blackout != null && Utilities.IsValid(player)) blackout.position = player.GetTrackingData(VRCPlayerApi.TrackingDataType.Head).position;
        if (t >= fadeIn + hold + fadeOut)
        {
            if (blackout != null) blackout.gameObject.SetActive(false);
            phase = 0; homed = false;
        }
    }

    private void Home()
    {
        homed = true;
        if (diveStation != null) diveStation.ExitStation(player);
        if (warp != null) warp.gameObject.SetActive(false);
        if (warpSound != null) warpSound.Stop();
        level = 0f;
        Calm();
        if (spawnPoint != null) player.TeleportTo(spawnPoint.position, spawnPoint.rotation);
    }

    private void Calm()
    {
        level = 0f;
        VRCShader.SetGlobalFloat(stormId, 0f);
        VRCShader.SetGlobalFloat(flashId, 0f);
        if (clock != null) { clock.storm = 0f; clock.white = 0f; clock.starsW = 0f; clock.flash = 0f; }
        if (savedSky != null) RenderSettings.skybox = savedSky;
        if (rain != null) rain.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        raining = false;
        if (rainSound != null) rainSound.Stop();
        SetAll(bolts, false);
        if (stair != null) stair.SetActive(false);
        stairShown = false;
        if (pole != null) pole.localScale = new Vector3(1f, 0.001f, 1f);
        OpenDome(false);
    }

    // ------------------------------------------------------------------ helpers
    private float Hash(float n) { float s = Mathf.Sin(n * 127.1f + 311.7f) * 43758.5453f; return s - Mathf.Floor(s); }

    private void SetAll(GameObject[] list, bool on)
    {
        if (list == null) return;
        for (int i = 0; i < list.Length; i++) if (list[i] != null && list[i].activeSelf != on) list[i].SetActive(on);
    }
}
