using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>v3: the Alcove of the Dead. Leave a water lily on the offering plinth; the lilies gather for everyone in the instance.</summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.Manual)]
public class HouseOffering : UdonSharpBehaviour
{
    public GameObject[] lilies;
    public AudioSource chime;
    public HouseQuest quest;           // leaving a lily completes the Keeper of the Dead quest: a candle is lit for you
    public int questIndex = 5;
    [UdonSynced] public int count;
    private int shown = -1;

    void Start() { Apply(); }

    public override void Interact()
    {
        if (quest != null) quest.Collect(questIndex);
        if (lilies == null || lilies.Length == 0) return;
        Networking.SetOwner(Networking.LocalPlayer, gameObject);
        count = Mathf.Min(count + 1, lilies.Length);
        RequestSerialization();
        Apply();
        if (chime != null) chime.Play();
    }

    public override void OnDeserialization() { Apply(); }

    private void Apply()
    {
        if (lilies == null || shown == count) return;
        shown = count;
        for (int i = 0; i < lilies.Length; i++) if (lilies[i] != null) lilies[i].SetActive(i < count);
    }
}
