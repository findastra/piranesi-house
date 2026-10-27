#nullable enable
// Compile-only stand-ins for the small part of Unity, VRChat and UdonSharp that HouseQuest, HouseQuestLink, HouseStorm and
// HouseStormLink use, so the real script files compile and run headlessly. These are NOT Unity: they copy only the names
// and signatures those scripts call. The real compile is UdonSharp in Unity 2022.3 on Astra's PC.
// Pattern from Unity Unicorn's Udon kits (scripts/udon-kits/Tests/Shims). Claude Opus 5.5 (claude-opus-5-5), 2026-10-26.
using System;
using System.Collections.Generic;

namespace UnityEngine
{
    public class Object { public string name = ""; }

    public class GameObject : Object
    {
        private bool active = true;
        public GameObject() { }
        public GameObject(string name) { this.name = name; }
        public bool activeSelf { get { return active; } }
        public void SetActive(bool value) { active = value; }
    }

    public class Component : Object
    {
        private GameObject? owner;
        public GameObject gameObject { get { return owner ??= new GameObject(GetType().Name); } }
    }

    public class Transform : Component
    {
        public Vector3 position, localPosition, localScale;
        public Quaternion rotation = Quaternion.identity;
    }

    public class Behaviour : Component { public bool enabled = true; }
    public class MonoBehaviour : Behaviour { }
    public class Material : Object { public void SetFloat(string name, float value) { } }
    public class AudioClip : Object { }

    public class AudioSource : Behaviour
    {
        public float volume = 1f;
        public bool isPlaying;
        public int plays;
        public void Play() { isPlaying = true; plays++; }
        public void Stop() { isPlaying = false; }
        public void PlayOneShot(AudioClip clip) { plays++; }
    }

    public enum ParticleSystemStopBehavior { StopEmittingAndClear, StopEmitting }

    public class ParticleSystem : Component
    {
        public int plays;
        public void Play() { plays++; }
        public void Stop(bool withChildren, ParticleSystemStopBehavior stopBehavior) { }
    }

    public static class RenderSettings { public static Material? skybox; }

    public struct Vector3
    {
        public float x, y, z;
        public Vector3(float x, float y, float z) { this.x = x; this.y = y; this.z = z; }
        public static Vector3 up { get { return new Vector3(0f, 1f, 0f); } }
        public static Vector3 operator +(Vector3 a, Vector3 b) { return new Vector3(a.x + b.x, a.y + b.y, a.z + b.z); }
        public static Vector3 operator *(Vector3 a, float d) { return new Vector3(a.x * d, a.y * d, a.z * d); }
        public static Vector3 Lerp(Vector3 a, Vector3 b, float t) { return a + new Vector3(b.x - a.x, b.y - a.y, b.z - a.z) * Mathf.Clamp01(t); }
    }

    public struct Quaternion
    {
        public float x, y, z, w;
        public static Quaternion identity { get { return new Quaternion { w = 1f }; } }
    }

    public static class Mathf
    {
        public const float PI = (float)Math.PI;
        public static int Min(int a, int b) { return Math.Min(a, b); }
        public static float Max(float a, float b) { return Math.Max(a, b); }
        public static int Clamp(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }
        public static float Clamp01(float v) { return v < 0f ? 0f : v > 1f ? 1f : v; }
        public static float Sin(float f) { return (float)Math.Sin(f); }
        public static float Pow(float f, float p) { return (float)Math.Pow(f, p); }
        public static float Floor(float f) { return (float)Math.Floor(f); }
        public static int FloorToInt(float f) { return (int)Math.Floor(f); }
        public static float InverseLerp(float a, float b, float v) { return a != b ? Clamp01((v - a) / (b - a)) : 0f; }
        public static float SmoothStep(float from, float to, float t) { t = Clamp01(t); t = -2f * t * t * t + 3f * t * t; return to * t + from * (1f - t); }
        public static float MoveTowards(float c, float t, float d) { return Math.Abs(t - c) <= d ? t : c + Math.Sign(t - c) * d; }
    }

    public static class Time { public static float time, deltaTime; }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class HeaderAttribute : Attribute { public HeaderAttribute(string header) { } }
}

namespace VRC.SDKBase
{
    using UnityEngine;

    public class VRCPlayerApi
    {
        public bool isLocal;
        public int playerId;
        public Vector3 position;

        public enum TrackingDataType { Head, LeftHand, RightHand, Origin }
        public struct TrackingData { public Vector3 position; public Quaternion rotation; }

        public Vector3 GetPosition() { return position; }
        public TrackingData GetTrackingData(TrackingDataType t) { return new TrackingData { position = position }; }
        public void TeleportTo(Vector3 p, Quaternion r) { position = p; }
    }

    public class VRCStation : Component
    {
        public void UseStation(VRCPlayerApi player) { }
        public void ExitStation(VRCPlayerApi player) { }
    }

    public static class VRCShader
    {
        public static int PropertyToID(string name) { return name.GetHashCode(); }
        public static void SetGlobalFloat(int id, float value) { }
    }

    public static class Networking
    {
        public static VRCPlayerApi? Local;
        public static VRCPlayerApi LocalPlayer { get { return Local!; } }
    }

    public static class Utilities
    {
        public static bool IsValid(object? obj) { return obj != null; }
    }
}

namespace VRC.SDK3.Persistence
{
    using VRC.SDKBase;

    /// <summary>
    /// VRChat's per-player saved data, modelled on its documented behaviour (creators.vrchat.com, Persistence, Player Data):
    /// the save arrives some time after joining; until then there is nothing to read, and "If you set PlayerData too
    /// early, it may be overwritten when the persistent data is received." Both outcomes of an early write are modelled:
    /// Overwritten (the save wins and the early write is lost) and Kept (the early write reaches the save and replaces
    /// what was there).
    /// </summary>
    public static class PlayerData
    {
        public enum EarlyWrite { Overwritten, Kept }

        private static readonly Dictionary<string, int> Saved = new Dictionary<string, int>();   // the save, across visits
        private static readonly Dictionary<string, int> Client = new Dictionary<string, int>();  // this visit's copy
        private static readonly Dictionary<string, int> Early = new Dictionary<string, int>();   // written before arrival
        private static bool arrived;
        public static int Writes, EarlyWrites;

        public static bool TryGetInt(VRCPlayerApi player, string key, out int value)
        {
            value = 0;
            return arrived && Client.TryGetValue(key, out value);
        }

        public static void SetInt(string key, int value)
        {
            Writes++;
            Client[key] = value;
            if (arrived) Saved[key] = value;
            else { Early[key] = value; EarlyWrites++; }
        }

        /// <summary>Test helper: a new visit. What was saved stays; nothing has arrived yet.</summary>
        public static void NewVisit()
        {
            Client.Clear(); Early.Clear(); arrived = false; Writes = 0; EarlyWrites = 0;
        }

        /// <summary>Test helper: forget everything (a player who never visited).</summary>
        public static void ResetForTest() { Saved.Clear(); NewVisit(); }

        /// <summary>Test helper: what the player had saved before this visit.</summary>
        public static void Seed(string key, int value) { Saved[key] = value; }

        /// <summary>Test helper: the save arrives (just before VRChat raises OnPlayerRestored).</summary>
        public static void Arrive(EarlyWrite mode)
        {
            if (mode == EarlyWrite.Kept) foreach (var kv in Early) Saved[kv.Key] = kv.Value;
            Client.Clear();
            foreach (var kv in Saved) Client[kv.Key] = kv.Value;
            Early.Clear();
            arrived = true;
        }

        /// <summary>Test helper: what is in the save now (what the next visit gets).</summary>
        public static int SavedValue(string key) { int v; return Saved.TryGetValue(key, out v) ? v : 0; }
    }
}

namespace UdonSharp
{
    using UnityEngine;
    using VRC.SDKBase;

    public enum BehaviourSyncMode { Any, Continuous, Manual, None, NoVariableSync }

    [AttributeUsage(AttributeTargets.Class)]
    public sealed class UdonBehaviourSyncModeAttribute : Attribute { public UdonBehaviourSyncModeAttribute(BehaviourSyncMode mode) { } }

    public abstract class UdonSharpBehaviour : MonoBehaviour
    {
        public readonly List<string> delayed = new List<string>();
        public bool DisableInteractive { get; set; }

        public virtual void Interact() { }
        public virtual void OnPlayerTriggerEnter(VRCPlayerApi player) { }
        public virtual void OnPlayerRestored(VRCPlayerApi player) { }

        /// <summary>Records the event name; the tests check what was scheduled.</summary>
        public void SendCustomEventDelayedSeconds(string eventName, float delaySeconds) { delayed.Add(eventName); }
    }
}

/// <summary>Stand-in for Piranesi House's HouseClock: only the fields HouseStorm writes.</summary>
public class HouseClock : UdonSharp.UdonSharpBehaviour
{
    public float storm, white, starsW, flash;
}
