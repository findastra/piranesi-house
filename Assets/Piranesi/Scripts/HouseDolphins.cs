using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// Occasionally a pod of dolphins passes the reef, leaping three times. The schedule comes from server time,
/// so everyone in the instance sees the same leaps without any network traffic.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseDolphins : UdonSharpBehaviour
{
    public Transform[] dolphins;
    public Vector3[] routeStart;
    public Vector3[] routeEnd;
    public float period = 95f;
    public float duration = 16f;
    public ParticleSystem splash;
    public AudioSource splashSound;
    public HouseClock clock;

    private float tide = 0.2f;
    private float[] lastY;

    public void SetTide(float t) { tide = t; }

    void Start()
    {
        lastY = new float[dolphins.Length];
        for (int i = 0; i < dolphins.Length; i++) if (dolphins[i] != null) dolphins[i].gameObject.SetActive(false);
    }

    void Update()
    {
        if (routeStart == null || routeStart.Length == 0) return;
        double t = Networking.GetServerTimeInSeconds();
        // server time / period stays far below int.MaxValue, and Udon only exposes % for int
        int cycle = (int)(t / period);
        float phase = (float)(t - cycle * (double)period);
        int route = cycle % routeStart.Length;
        for (int k = 0; k < dolphins.Length; k++)
        {
            Transform d = dolphins[k];
            if (d == null) continue;
            float local = phase - k * 0.9f;
            if (local < 0f || local > duration)
            {
                if (d.gameObject.activeSelf) d.gameObject.SetActive(false);
                continue;
            }
            if (!d.gameObject.activeSelf) d.gameObject.SetActive(true);
            float u = local / duration;
            Vector3 a = routeStart[route]; Vector3 b = routeEnd[route];
            Vector3 dir = (b - a); dir.y = 0f; dir.Normalize();
            Vector3 side = Vector3.Cross(Vector3.up, dir);
            Vector3 p = Vector3.Lerp(a, b, u) + side * ((k - 1) * 1.6f);
            // three leaps between u = 0.25 and 0.85, otherwise cruising just under the surface
            float leap = 0f, dleap = 0f;
            if (u > 0.25f && u < 0.85f)
            {
                float f = (u - 0.25f) / 0.6f * 3f;
                float frac = f - Mathf.Floor(f);
                leap = Mathf.Sin(frac * Mathf.PI);
                dleap = Mathf.Cos(frac * Mathf.PI);
            }
            float y = tide - 0.9f + leap * 2.4f;
            p.y = y;
            float pitch = -dleap * 35f;
            d.SetPositionAndRotation(p, Quaternion.LookRotation(dir) * Quaternion.Euler(pitch, 0f, 0f));
            // splash when crossing the surface
            if (splash != null && (lastY[k] - tide) * (y - tide) < 0f)
            {
                splash.transform.position = new Vector3(p.x, tide, p.z);
                splash.Emit(40);
                if (splashSound != null) { splashSound.transform.position = splash.transform.position; splashSound.Play(); }
            }
            lastY[k] = y;
        }
    }
}
