using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// A place to sit: window seats, the Colossus' palm, hammocks, boat seats. Interact (on this object or a
/// separate trigger that calls Sit) puts the local player into the station. Optionally drives a boat.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseSeat : UdonSharpBehaviour
{
    public VRCStation station;
    public HouseBoat boat;
    public bool isDriver;
    public AudioSource enterSound;

    public override void Interact()
    {
        Sit();
    }

    public void Sit()
    {
        if (station == null) return;
        VRCPlayerApi lp = Networking.LocalPlayer;
        if (lp == null) return;
        station.UseStation(lp);
    }

    public override void OnStationEntered(VRCPlayerApi player)
    {
        if (player == null || !player.isLocal) return;
        if (enterSound != null) enterSound.Play();
        if (boat != null && isDriver) boat.BeginDrive();
    }

    public override void OnStationExited(VRCPlayerApi player)
    {
        if (player == null || !player.isLocal) return;
        if (boat != null && isDriver) boat.EndDrive();
    }
}
