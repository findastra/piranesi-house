using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// Local footsteps. Marble by default, sand when standing on anything named "Sand*",
/// splashing when the tide is above the player's feet. Stride follows walking speed.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseFootsteps : UdonSharpBehaviour
{
    public AudioSource source;
    public AudioClip[] marble;
    public AudioClip[] sand;
    public AudioClip[] water;
    public float strideWalk = 0.72f;
    public float strideRun = 1.05f;
    public float volume = 0.75f;
    public LayerMask groundMask = 1;

    private float travelled;
    private int lastIndex = -1;
    private float tide = -10f;

    public void SetTide(float t) { tide = t; }

    void Update()
    {
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (lp == null || source == null) return;
        if (!lp.IsPlayerGrounded()) { travelled = 0.5f * strideWalk; return; }
        Vector3 v = lp.GetVelocity();
        v.y = 0f;
        float speed = v.magnitude;
        if (speed < 0.35f) { travelled = Mathf.Min(travelled, 0.3f); return; }
        travelled += speed * Time.deltaTime;
        float stride = Mathf.Lerp(strideWalk, strideRun, Mathf.InverseLerp(2f, 5f, speed));
        if (travelled < stride) return;
        travelled = 0f;

        Vector3 feet = lp.GetPosition();
        AudioClip[] set = marble;
        float vol = volume * Mathf.Lerp(0.55f, 1f, Mathf.InverseLerp(0.5f, 5f, speed));
        float depth = tide - feet.y;
        if (depth > 0.04f)
        {
            set = water;
            vol *= Mathf.Lerp(0.7f, 1.2f, Mathf.Clamp01(depth / 0.6f));
        }
        else
        {
            RaycastHit hit;
            if (Physics.Raycast(feet + Vector3.up * 0.4f, Vector3.down, out hit, 1.2f, groundMask.value))
            {
                if (hit.collider != null && hit.collider.gameObject.name.StartsWith("Sand")) { set = sand; vol *= 0.8f; }
            }
        }
        if (set == null || set.Length == 0) return;
        int i = Random.Range(0, set.Length);
        if (i == lastIndex && set.Length > 1) i = (i + 1) % set.Length;
        lastIndex = i;
        source.transform.position = feet + Vector3.up * 0.05f;
        source.pitch = Random.Range(0.92f, 1.08f);
        source.PlayOneShot(set[i], vol);
    }
}
