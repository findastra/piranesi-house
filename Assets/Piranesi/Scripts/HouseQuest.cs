using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRC.SDK3.Persistence;

/// <summary>
/// v3 the Far Hall Quests (6 / 6), for each player on their own. One prize in each far hall, matching that road's lesson:
///   0 a page of Piranesi's journal (the Rememberer)   1 a gold-mended shard (the Mender)      2 golden honeycomb (the Beekeeper)
///   3 a cloud in a jar (the Cloud-Walker)              4 Ariadne's golden thread (the Thread-Bearer)
///   5 a candle lit for you (Keeper of the Dead: leave a water lily on the offering plinth in the Alcove of the Dead)
/// Taking one: a chime, a burst of glints, the prize leaves its hall and its twin appears on the shelf at the spawn camp
/// by its role plaque, and the plaques on the quest stand count FAR HALL QUESTS 0 / 6 .. 6 / 6. Taking the thread lights
/// Ariadne's golden thread on the floors of the labyrinth, leading home. Saved to the player (PlayerData).
/// No prize waits on the tide or needs a second player.
/// </summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseQuest : UdonSharpBehaviour
{
    public GameObject[] prizes;        // in the far halls (0..4 leave when taken; 5 is the candle, which lights when done)
    public GameObject[] pickups;       // the interact triggers by each prize (switched off once taken)
    public GameObject[] shelf;         // the twins on the shelf at the camp
    public GameObject[] counts;        // the plaques 0/6 .. 6/6
    public ParticleSystem[] glints;    // a burst at each prize
    public AudioSource chime;
    public GameObject thread;          // Ariadne's golden thread (prize 4)
    public int threadIndex = 4;
    public int candleIndex = 5;

    private const string Key = "piranesi.quests";
    private int got;

    void Start() { Apply(); }

    public override void OnPlayerRestored(VRCPlayerApi p)
    {
        if (!Utilities.IsValid(p) || !p.isLocal) return;
        int v;
        if (PlayerData.TryGetInt(p, Key, out v)) got = v & 63;
        Apply();
    }

    public void Collect(int i)
    {
        if (i < 0 || i > 5) return;
        int bit = 1 << i;
        if ((got & bit) != 0) return;
        got |= bit;
        PlayerData.SetInt(Key, got);
        if (chime != null) chime.Play();
        if (glints != null && i < glints.Length && glints[i] != null) glints[i].Play();
        Apply();
    }

    public bool Has(int i) { return (got & (1 << i)) != 0; }

    private void Apply()
    {
        int n = 0;
        for (int i = 0; i < 6; i++)
        {
            bool has = (got & (1 << i)) != 0;
            if (has) n++;
            if (prizes != null && i < prizes.Length && prizes[i] != null) prizes[i].SetActive(i == candleIndex ? has : !has);
            if (pickups != null && i < pickups.Length && pickups[i] != null && i != candleIndex) pickups[i].SetActive(!has);
            if (shelf != null && i < shelf.Length && shelf[i] != null) shelf[i].SetActive(has);
        }
        if (counts != null) for (int k = 0; k < counts.Length; k++) if (counts[k] != null) counts[k].SetActive(k == n);
        if (thread != null) thread.SetActive(Has(threadIndex));
    }
}
