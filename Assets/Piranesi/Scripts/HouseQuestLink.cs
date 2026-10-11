using UdonSharp;
using UnityEngine;
using VRC.SDKBase;

/// <summary>v3: the interact by a Far Hall Quest prize ("Take ..."): hands the prize to HouseQuest.</summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseQuestLink : UdonSharpBehaviour
{
    public HouseQuest quest;
    public int index;

    public override void Interact()
    {
        if (quest != null) quest.Collect(index);
    }
}
