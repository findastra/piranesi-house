using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// v3: the Climb vine beside the Colossus' raised hand. It carries no label: its "Climb" prompt only appears while you are
/// standing in the hand (within nearRadius of 'near'). Interact and you stand on the roofs at the castellum.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseTeleport : UdonSharpBehaviour
{
    public Transform target;
    public AudioSource sound;
    public Transform near;
    public float nearRadius = 2.4f;
    private VRCPlayerApi player;
    private bool open = true;
    private float check;

    void Start()
    {
        player = Networking.LocalPlayer;
        if (near != null) { open = false; DisableInteractive = true; }
    }

    void Update()
    {
        if (near == null) return;
        check -= Time.deltaTime;
        if (check > 0f) return;
        check = 0.2f;
        if (!Utilities.IsValid(player)) { player = Networking.LocalPlayer; return; }
        bool want = Vector3.Distance(player.GetPosition(), near.position) <= nearRadius;
        if (want != open) { open = want; DisableInteractive = !want; }
    }

    public override void Interact()
    {
        if (!Utilities.IsValid(player) || target == null) return;
        if (sound != null) sound.Play();
        player.TeleportTo(target.position, target.rotation);
    }
}
