using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// v3: small links into the Stormscape. mode 0: a dead-end hall (walking in counts it); mode 1: the secret rosette on the
/// Colossus' pedestal (interact: starts the storm); mode 2: Astra's phone booth on the landing at the top of the stair
/// (stepping inside starts the End Show; no click).
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseStormLink : UdonSharpBehaviour
{
    public HouseStorm storm;
    public int mode;
    public int index;

    void Start()
    {
        if (mode != 1) DisableInteractive = true;
    }

    public override void Interact()
    {
        if (storm != null && mode == 1) storm.BeginStorm();
    }

    public override void OnPlayerTriggerEnter(VRCPlayerApi player)
    {
        if (storm == null || !Utilities.IsValid(player) || !player.isLocal) return;
        if (mode == 0) storm.Found(index);
        else if (mode == 2) storm.BeginEndShow();
    }
}
