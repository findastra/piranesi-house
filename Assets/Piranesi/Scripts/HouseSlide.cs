using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// The water slide from the top of the stair tower to the lagoon. Interact at the top to ride: you sit on a
/// sled that follows the flume spline with gravity-like speed, then splash down and step out by the beach.
/// One rider at a time; the sled position is synced so everyone sees the ride.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.Continuous)]
public class HouseSlide : UdonSharpBehaviour
{
    public VRCStation station;
    public Transform sled;
    public Vector3[] path;
    public Transform exitPoint;
    public AudioSource rideSound;
    public AudioSource splashSound;
    public ParticleSystem splashFx;
    public float minSpeed = 3f;
    public float maxSpeed = 15f;

    [UdonSynced(UdonSyncMode.Linear)] public float syncDist = -1f;

    private float[] cum;
    private float total;
    private float dist = -1f;
    private float speed;
    private bool riding;

    void Start()
    {
        if (path == null || path.Length < 2) return;
        cum = new float[path.Length];
        cum[0] = 0f;
        for (int i = 1; i < path.Length; i++) cum[i] = cum[i - 1] + Vector3.Distance(path[i - 1], path[i]);
        total = cum[path.Length - 1];
        PlaceSled(0f);
    }

    public override void Interact()
    {
        if (riding || cum == null) return;
        if (syncDist > 0f && syncDist < total - 0.5f && !Networking.IsOwner(gameObject)) return; // someone is mid-ride
        Networking.SetOwner(Networking.LocalPlayer, gameObject);
        dist = 0f; speed = minSpeed; riding = true;
        PlaceSled(0f);
        station.UseStation(Networking.LocalPlayer);
        if (rideSound != null) rideSound.Play();
    }

    private void PlaceSled(float d)
    {
        if (cum == null || sled == null) return;
        int i = 0;
        while (i < path.Length - 2 && cum[i + 1] < d) i++;
        float seg = Mathf.Max(cum[i + 1] - cum[i], 0.0001f);
        float f = Mathf.Clamp01((d - cum[i]) / seg);
        Vector3 p = Vector3.Lerp(path[i], path[i + 1], f);
        Vector3 tg = path[i + 1] - path[i];
        sled.position = p;
        if (tg.sqrMagnitude > 0.0001f) sled.rotation = Quaternion.LookRotation(tg.normalized, Vector3.up);
    }

    void Update()
    {
        if (cum == null) return;
        if (riding)
        {
            float dt = Time.deltaTime;
            int i = 0;
            while (i < path.Length - 2 && cum[i + 1] < dist) i++;
            float seg = Mathf.Max(cum[i + 1] - cum[i], 0.0001f);
            float slope = (path[i].y - path[i + 1].y) / seg;
            speed += (9.81f * slope - 0.012f * speed * speed) * dt;
            speed = Mathf.Clamp(speed, minSpeed, maxSpeed);
            dist += speed * dt;
            syncDist = dist;
            PlaceSled(dist);
            if (dist >= total)
            {
                riding = false;
                syncDist = -1f;
                VRCPlayerApi lp = Networking.LocalPlayer;
                station.ExitStation(lp);
                if (exitPoint != null) lp.TeleportTo(exitPoint.position, exitPoint.rotation);
                if (splashSound != null) splashSound.Play();
                if (splashFx != null) splashFx.Play();
                if (rideSound != null) rideSound.Stop();
                PlaceSled(0f);
            }
        }
        else if (!Networking.IsOwner(gameObject))
        {
            if (syncDist >= 0f) PlaceSled(syncDist);
            else PlaceSled(0f);
        }
    }
}
