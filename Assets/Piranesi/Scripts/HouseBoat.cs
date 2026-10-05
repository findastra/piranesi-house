using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRC.Udon.Common;

/// <summary>
/// Venetian long canoe. The player in the stern seat rows with the movement input (forward/back + turn).
/// Floats on the live tide, bobs gently, stops at walls, and runs aground softly on beaches so you can
/// step off onto the sand. Position/heading are synced from the driver to everyone else.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.Continuous)]
public class HouseBoat : UdonSharpBehaviour
{
    public float maxSpeed = 3.4f;
    public float accel = 1.4f;
    public float drag = 0.6f;
    public float turnRate = 42f;
    public float draft = 0.32f;
    public float halfLength = 3.6f;
    public LayerMask hitMask = 1;
    public AudioSource paddleSound;

    [UdonSynced(UdonSyncMode.Linear)] public Vector3 syncPos;
    [UdonSynced(UdonSyncMode.Linear)] public float syncYaw;

    private float tide = 0.2f;
    private float speed;
    private float yaw;
    private float inV, inH;
    private bool driving;
    private Vector3 pos;
    private float paddleTimer;

    void Start()
    {
        pos = transform.position;
        yaw = transform.eulerAngles.y;
        syncPos = pos; syncYaw = yaw;
    }

    public void SetTide(float t) { tide = t; }

    public void BeginDrive()
    {
        driving = true;
        Networking.SetOwner(Networking.LocalPlayer, gameObject);
        pos = transform.position; yaw = transform.eulerAngles.y;
    }

    public void EndDrive()
    {
        driving = false; inV = 0f; inH = 0f;
    }

    public override void InputMoveVertical(float value, UdonInputEventArgs args)
    {
        if (driving) inV = value;
    }

    public override void InputMoveHorizontal(float value, UdonInputEventArgs args)
    {
        if (driving) inH = value;
    }

    void Update()
    {
        float dt = Time.deltaTime;
        if (Networking.IsOwner(gameObject))
        {
            float target = inV * maxSpeed;
            if (Mathf.Abs(inV) > 0.05f) speed = Mathf.MoveTowards(speed, target, accel * dt);
            else speed = Mathf.MoveTowards(speed, 0f, drag * dt);
            yaw += inH * turnRate * dt * Mathf.Clamp01(0.35f + Mathf.Abs(speed) / maxSpeed);

            Vector3 fwd = Quaternion.Euler(0f, yaw, 0f) * Vector3.forward;
            float dir = speed >= 0f ? 1f : -1f;
            Vector3 eye = new Vector3(pos.x, tide + 0.35f, pos.z);
            RaycastHit hit;
            if (Mathf.Abs(speed) > 0.01f && Physics.Raycast(eye, fwd * dir, out hit, halfLength + 0.6f + Mathf.Abs(speed) * 0.4f, hitMask.value, QueryTriggerInteraction.Ignore))
            {
                speed = 0f;   // bumped into a wall, rock or the stairs
            }
            Vector3 next = pos + fwd * speed * dt;
            // shallow water: slow down and run aground on sand
            Vector3 bow = next + fwd * halfLength * dir;
            if (Physics.Raycast(new Vector3(bow.x, tide + 3f, bow.z), Vector3.down, out hit, 30f, hitMask.value, QueryTriggerInteraction.Ignore))
            {
                float depth = tide - hit.point.y;
                if (depth < draft) { speed *= Mathf.Clamp01(depth / draft); if (depth < 0.05f) next = pos; }
            }
            pos = next;
            syncPos = pos; syncYaw = yaw;

            if (driving && Mathf.Abs(inV) > 0.2f)
            {
                paddleTimer -= dt;
                if (paddleTimer <= 0f && paddleSound != null) { paddleSound.pitch = Random.Range(0.9f, 1.1f); paddleSound.Play(); paddleTimer = 1.3f; }
            }
        }
        else
        {
            pos = syncPos; yaw = syncYaw;
        }
        float t = Time.time;
        float bob = Mathf.Sin(t * 1.1f + pos.x * 0.1f) * 0.04f;
        float roll = Mathf.Sin(t * 0.9f + pos.z * 0.13f) * 1.5f;
        float pitch = Mathf.Sin(t * 0.7f) * 0.8f - speed * 0.4f;
        transform.SetPositionAndRotation(new Vector3(pos.x, tide + bob, pos.z), Quaternion.Euler(pitch, yaw, roll));
    }
}
