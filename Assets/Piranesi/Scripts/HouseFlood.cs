using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// v3: the Joining of the Three Tides in the Ninth Vestibule. Every 'period' seconds (from the shared server clock, so the
/// whole instance sees it together) the water rises from 'low' to 'high', holds, and drains again.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseFlood : UdonSharpBehaviour
{
    public Transform water;
    public AudioSource roar;
    public ParticleSystem[] sprays;
    public float low = -0.4f, high = 1.2f, period = 420f, rise = 24f, hold = 40f, offset = 90f;
    private bool on;

    void Update()
    {
        if (water == null) return;
        float t = (float)((Networking.GetServerTimeInSeconds() + offset) % period);
        float k;
        if (t < rise) k = Mathf.SmoothStep(0f, 1f, t / rise);
        else if (t < rise + hold) k = 1f;
        else if (t < rise * 2f + hold) k = Mathf.SmoothStep(1f, 0f, (t - rise - hold) / rise);
        else k = 0f;
        Vector3 p = water.position; p.y = Mathf.Lerp(low, high, k); water.position = p;
        bool want = k > 0.01f;
        if (want != on)
        {
            on = want;
            if (roar != null) { if (on) roar.Play(); else roar.Stop(); }
            if (sprays != null) for (int i = 0; i < sprays.Length; i++) if (sprays[i] != null) { if (on) sprays[i].Play(); else sprays[i].Stop(); }
        }
        if (roar != null && on) roar.volume = 0.25f + 0.65f * k;
    }
}
