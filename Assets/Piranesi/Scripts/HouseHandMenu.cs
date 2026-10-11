using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>
/// A small card about Piranesi (Audible + a bookshop, as QR codes) that only the local player sees.
/// VR: raise your left hand in front of your face and hold it there for a moment; lower it to put the card away.
/// Desktop: press M to show or hide it in front of you.
/// VRChat worlds cannot open web pages or sign in to other services, so the card carries QR codes to scan with a phone.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseHandMenu : UdonSharpBehaviour
{
    public Transform card;
    public float vrHeight = 0.2f;            // card height in metres when held
    public float desktopHeight = 0.36f;
    public float desktopDistance = 0.6f;
    public float showDistance = 0.48f;        // hand within this distance of the head
    public float inFront = 0.6f;              // cos of the angle between the gaze and the hand
    public float dwell = 0.5f;                // seconds the gesture is held before the card appears

    private VRCPlayerApi local;
    private bool vr;
    private bool desktopOpen;
    private float hold;
    private float vis;

    void Start()
    {
        local = Networking.LocalPlayer;
        if (local != null) vr = local.IsUserInVR();
        if (card != null) card.gameObject.SetActive(false);
    }

    void Update()
    {
        if (local == null || card == null) return;
        VRCPlayerApi.TrackingData head = local.GetTrackingData(VRCPlayerApi.TrackingDataType.Head);
        Vector3 hp = head.position;
        Vector3 fwd = head.rotation * Vector3.forward;
        bool want;
        Vector3 pos;
        Quaternion rot;
        float h;
        if (vr)
        {
            VRCPlayerApi.TrackingData hand = local.GetTrackingData(VRCPlayerApi.TrackingDataType.LeftHand);
            Vector3 toHand = hand.position - hp;
            float dist = toHand.magnitude;
            Vector3 dir = dist > 0.001f ? toHand / dist : fwd;
            bool gesture = dist < showDistance && Vector3.Dot(fwd, dir) > inFront && hand.position.y > hp.y - 0.35f;
            hold = gesture ? hold + Time.deltaTime : 0f;
            want = gesture && (hold > dwell || vis > 0.01f);
            pos = hand.position + (hp - hand.position) * 0.12f + Vector3.up * (vrHeight * 0.6f);
            rot = Quaternion.LookRotation(pos - hp, Vector3.up);
            h = vrHeight;
        }
        else
        {
            if (Input.GetKeyDown(KeyCode.M)) desktopOpen = !desktopOpen;
            want = desktopOpen;
            pos = hp + fwd * desktopDistance;
            rot = Quaternion.LookRotation(fwd, head.rotation * Vector3.up);
            h = desktopHeight;
        }
        vis = Mathf.MoveTowards(vis, want ? 1f : 0f, Time.deltaTime * 5f);
        bool on = vis > 0.001f;
        if (card.gameObject.activeSelf != on) card.gameObject.SetActive(on);
        if (!on) return;
        float k = Mathf.SmoothStep(0f, 1f, vis);
        card.SetPositionAndRotation(pos, rot);
        card.localScale = new Vector3(h * 0.8f, h, 1f) * k;
    }
}
