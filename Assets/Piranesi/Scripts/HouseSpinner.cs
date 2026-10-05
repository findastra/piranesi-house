using UdonSharp;
using UnityEngine;

/// <summary>Turns a transform steadily about one of its local axes (the noria water wheel).</summary>
[UdonBehaviourSyncMode(BehaviourSyncMode.None)]
public class HouseSpinner : UdonSharpBehaviour
{
    public Vector3 axis = Vector3.right;
    public float degreesPerSecond = 9f;

    void Update()
    {
        transform.Rotate(axis, degreesPerSecond * Time.deltaTime, Space.Self);
    }
}
