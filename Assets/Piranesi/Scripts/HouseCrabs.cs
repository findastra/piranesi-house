using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// Beach crabs: each wanders sideways around its home spot, pauses, and scuttles away when you come close.
/// Local simulation (cosmetic), snapped to the sand with a downward ray.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseCrabs : UdonSharpBehaviour
{
    public Transform[] crabs;
    public float wanderRadius = 3f;
    public float speed = 0.45f;
    public float fleeSpeed = 1.6f;
    public float fleeDistance = 2.5f;
    public LayerMask groundMask = 1;

    private Vector3[] home;
    private Vector3[] target;
    private float[] wait;
    private float[] heading;
    private int next;

    void Start()
    {
        int n = crabs.Length;
        home = new Vector3[n]; target = new Vector3[n]; wait = new float[n]; heading = new float[n];
        for (int i = 0; i < n; i++)
        {
            if (crabs[i] == null) continue;
            home[i] = crabs[i].position; target[i] = home[i];
            wait[i] = Random.Range(0f, 4f); heading[i] = crabs[i].eulerAngles.y;
        }
    }

    void Update()
    {
        if (home == null) return;
        VRCPlayerApi lp = Networking.LocalPlayer;
        Vector3 pp = lp != null ? lp.GetPosition() : new Vector3(9999f, 0f, 9999f);
        float dt = Time.deltaTime;
        for (int i = 0; i < crabs.Length; i++)
        {
            Transform c = crabs[i];
            if (c == null) continue;
            Vector3 p = c.position;
            Vector3 away = p - pp; away.y = 0f;
            bool flee = away.sqrMagnitude < fleeDistance * fleeDistance;
            float v = speed;
            if (flee)
            {
                target[i] = p + away.normalized * 2.5f; v = fleeSpeed; wait[i] = 0f;
            }
            else if (wait[i] > 0f)
            {
                wait[i] -= dt; continue;
            }
            Vector3 d = target[i] - p; d.y = 0f;
            if (d.magnitude < 0.08f)
            {
                Vector2 r = Random.insideUnitCircle * wanderRadius;
                target[i] = home[i] + new Vector3(r.x, 0f, r.y);
                wait[i] = Random.Range(1.5f, 6f);
                continue;
            }
            Vector3 step = d.normalized * v * dt;
            p += step;
            RaycastHit hit;
            if (Physics.Raycast(p + Vector3.up * 1.5f, Vector3.down, out hit, 4f, groundMask.value, QueryTriggerInteraction.Ignore)) p.y = hit.point.y;
            // crabs walk sideways: face 90 degrees from the direction of travel
            float want = Mathf.Atan2(step.x, step.z) * Mathf.Rad2Deg + 90f;
            heading[i] = Mathf.MoveTowardsAngle(heading[i], want, 360f * dt);
            c.SetPositionAndRotation(p, Quaternion.Euler(0f, heading[i], Mathf.Sin(Time.time * 18f + i) * 2f));
        }
    }
}
