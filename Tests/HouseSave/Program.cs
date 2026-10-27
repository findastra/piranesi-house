#nullable enable
// Headless save tests for Piranesi House: the Far Hall Quests (HouseQuest) and the dead ends (HouseStorm) save to the
// player with PlayerData. VRChat's save arrives some time after joining, and a write made before it arrives "may be
// overwritten when the persistent data is received" (VRChat creator docs). These tests run the real script files, compiled
// against Shims.cs, through a find made before the save arrives, under both outcomes of that early write.
// Run: dotnet run -c Release (from this folder). No packages; exits 1 on any failure.
// Claude Opus 5.5 (claude-opus-5-5), 2026-10-26.
using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using VRC.SDK3.Persistence;
using VRC.SDKBase;

public static class Program
{
    private const string QuestKey = "piranesi.quests";
    private const string DeadEndKey = "piranesi.deadends";
    private static readonly VRCPlayerApi Me = new VRCPlayerApi { isLocal = true, playerId = 1 };

    private sealed class CheckFailed : Exception { public CheckFailed(string m) : base(m) { } }

    private static void True(bool ok, string what) { if (!ok) throw new CheckFailed(what); }

    private static void Equal(int expected, int actual, string what)
    {
        if (expected != actual) throw new CheckFailed(what + ": expected " + expected + ", got " + actual);
    }

    private static void EqualMask(int expected, int actual, string what)
    {
        if (expected != actual) throw new CheckFailed(what + ": expected " + Bits(expected) + ", got " + Bits(actual));
    }

    private static string Bits(int v) { return "0b" + Convert.ToString(v, 2); }

    private static void CallStart(object o)
    {
        MethodInfo? m = o.GetType().GetMethod("Start", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
        if (m != null) m.Invoke(o, null);
    }

    private static GameObject[] Objects(int n, string name)
    {
        var a = new GameObject[n];
        for (int i = 0; i < n; i++) a[i] = new GameObject(name + i);
        return a;
    }

    private static int Active(GameObject[] list)
    {
        int at = -1;
        for (int i = 0; i < list.Length; i++) if (list[i].activeSelf) { True(at < 0, "only one plaque is on"); at = i; }
        return at;
    }

    // ---------------------------------------------------------------- the Far Hall Quests

    private static HouseQuest Quest()
    {
        var glints = new ParticleSystem[6];
        for (int i = 0; i < 6; i++) glints[i] = new ParticleSystem();
        var q = new HouseQuest
        {
            prizes = Objects(6, "prize"), pickups = Objects(6, "pickup"), shelf = Objects(6, "shelf"),
            counts = Objects(7, "count"), glints = glints, chime = new AudioSource(), thread = new GameObject("thread"),
        };
        CallStart(q);
        return q;
    }

    private static void Take(HouseQuest q, int i)
    {
        var link = new HouseQuestLink { quest = q, index = i };
        link.Interact();
    }

    private static void ShowsQuest(HouseQuest q, int mask, string at)
    {
        int n = 0;
        for (int i = 0; i < 6; i++)
        {
            bool has = (mask & (1 << i)) != 0;
            if (has) n++;
            True(q.Has(i) == has, "prize " + i + (has ? " is taken" : " is not taken") + at);
            True(q.shelf[i].activeSelf == has, "shelf twin " + i + (has ? " is on" : " is off") + at);
            True(q.prizes[i].activeSelf == (i == q.candleIndex ? has : !has), "prize " + i + " in its hall" + at);
        }
        Equal(n, Active(q.counts), "the count plaque" + at);
        True(q.thread.activeSelf == ((mask & (1 << q.threadIndex)) != 0), "Ariadne's thread" + at);
    }

    private static void QuestEarlyTake(PlayerData.EarlyWrite mode)
    {
        string at = " (early write " + mode + ")";
        PlayerData.Seed(QuestKey, 0b010111);          // an earlier visit: the journal page, the shard, the honeycomb, the thread
        PlayerData.NewVisit();
        var q = Quest();
        Take(q, 3);                                   // the cloud in a jar, taken before the save arrives
        True(q.Has(3), "the cloud is taken at once" + at);
        PlayerData.Arrive(mode);
        q.OnPlayerRestored(Me);
        ShowsQuest(q, 0b011111, " after the save arrives" + at);
        EqualMask(0b011111, PlayerData.SavedValue(QuestKey), "saved: the earlier visit's four and the cloud" + at);

        PlayerData.NewVisit();                        // next visit
        var next = Quest();
        PlayerData.Arrive(PlayerData.EarlyWrite.Overwritten);
        next.OnPlayerRestored(Me);
        ShowsQuest(next, 0b011111, " on the next visit" + at);
    }

    public static void QuestEarlyTakeWhenTheSaveWins() { QuestEarlyTake(PlayerData.EarlyWrite.Overwritten); }

    public static void QuestEarlyTakeWhenTheEarlyWriteWins() { QuestEarlyTake(PlayerData.EarlyWrite.Kept); }

    public static void QuestSavesNothingBeforeTheSaveArrives()
    {
        PlayerData.Seed(QuestKey, 0b000001);
        PlayerData.NewVisit();
        var q = Quest();
        Take(q, 2);
        Take(q, 5);
        Equal(0, PlayerData.EarlyWrites, "PlayerData writes before OnPlayerRestored");
    }

    public static void QuestSavesEachPrizeOnceTheSaveHasArrived()
    {
        PlayerData.Seed(QuestKey, 0b000001);
        PlayerData.NewVisit();
        var q = Quest();
        PlayerData.Arrive(PlayerData.EarlyWrite.Overwritten);
        q.OnPlayerRestored(Me);
        ShowsQuest(q, 0b000001, " restored");
        Equal(0, PlayerData.Writes, "no write when nothing new was taken");
        Take(q, 2);
        EqualMask(0b000101, PlayerData.SavedValue(QuestKey), "saved at once");
        Take(q, 2);
        Equal(1, PlayerData.Writes, "taking a prize twice saves once");
    }

    public static void QuestFirstVisitStartsAtNothing()
    {
        PlayerData.NewVisit();
        var q = Quest();
        PlayerData.Arrive(PlayerData.EarlyWrite.Overwritten);
        q.OnPlayerRestored(Me);
        ShowsQuest(q, 0, " on a first visit");
        Equal(0, PlayerData.Writes, "nothing written for a player with no save");
    }

    // ---------------------------------------------------------------- the dead ends

    private static HouseStorm Storm()
    {
        var bursts = new ParticleSystem[5];
        for (int i = 0; i < 5; i++) bursts[i] = new ParticleSystem();
        var s = new HouseStorm { tally = Objects(6, "tally"), bursts = bursts, chime = new AudioSource() };
        CallStart(s);
        return s;
    }

    private static void WalkInto(HouseStorm s, int i)
    {
        var link = new HouseStormLink { storm = s, mode = 0, index = i };
        CallStart(link);
        link.OnPlayerTriggerEnter(Me);
    }

    private static void DeadEndEarlyFind(PlayerData.EarlyWrite mode)
    {
        string at = " (early write " + mode + ")";
        PlayerData.Seed(DeadEndKey, 0b00101);
        PlayerData.NewVisit();
        var s = Storm();
        WalkInto(s, 1);
        PlayerData.Arrive(mode);
        s.OnPlayerRestored(Me);
        Equal(3, s.Count(), "dead ends found" + at);
        Equal(3, Active(s.tally), "the tally plaque" + at);
        EqualMask(0b00111, PlayerData.SavedValue(DeadEndKey), "saved: the earlier two and the new one" + at);
        True(s.delayed.Count == 0, "no storm at 3 / 5" + at);
    }

    public static void DeadEndEarlyFindWhenTheSaveWins() { DeadEndEarlyFind(PlayerData.EarlyWrite.Overwritten); }

    public static void DeadEndEarlyFindWhenTheEarlyWriteWins() { DeadEndEarlyFind(PlayerData.EarlyWrite.Kept); }

    public static void DeadEndSavesNothingBeforeTheSaveArrives()
    {
        PlayerData.NewVisit();
        var s = Storm();
        WalkInto(s, 0);
        Equal(0, PlayerData.EarlyWrites, "PlayerData writes before OnPlayerRestored");
    }

    public static void AnEarlyFifthDeadEndStillBringsTheStorm()
    {
        PlayerData.Seed(DeadEndKey, 0b01111);
        PlayerData.NewVisit();
        var s = Storm();
        WalkInto(s, 4);
        PlayerData.Arrive(PlayerData.EarlyWrite.Overwritten);
        s.OnPlayerRestored(Me);
        Equal(5, s.Count(), "all five dead ends");
        True(s.delayed.Contains("BeginStorm"), "the fifth dead end starts the storm");
        EqualMask(0b11111, PlayerData.SavedValue(DeadEndKey), "saved: all five");
    }

    public static void AReturningPlayerWithAllFiveGetsNoStormOnArrival()
    {
        PlayerData.Seed(DeadEndKey, 0b11111);
        PlayerData.NewVisit();
        var s = Storm();
        PlayerData.Arrive(PlayerData.EarlyWrite.Overwritten);
        s.OnPlayerRestored(Me);
        Equal(5, s.Count(), "all five shown");
        True(s.delayed.Count == 0, "no storm just for arriving (the rosette starts it again)");
        Equal(0, PlayerData.Writes, "nothing written");
    }

    public static void DeadEndSavesEachFindOnceTheSaveHasArrived()
    {
        PlayerData.NewVisit();
        var s = Storm();
        PlayerData.Arrive(PlayerData.EarlyWrite.Overwritten);
        s.OnPlayerRestored(Me);
        WalkInto(s, 2);
        EqualMask(0b00100, PlayerData.SavedValue(DeadEndKey), "saved at once");
    }

    // ---------------------------------------------------------------- runner

    public static int Main()
    {
        Networking.Local = Me;
        var tests = new List<MethodInfo>();
        foreach (MethodInfo m in typeof(Program).GetMethods(BindingFlags.Public | BindingFlags.Static))
            if (m.Name != "Main" && m.GetParameters().Length == 0 && m.ReturnType == typeof(void)) tests.Add(m);

        int failed = 0;
        foreach (MethodInfo m in tests)
        {
            PlayerData.ResetForTest();
            try
            {
                m.Invoke(null, null);
                Console.WriteLine("ok     " + m.Name);
            }
            catch (TargetInvocationException e)
            {
                failed++;
                Console.WriteLine("FAILED " + m.Name + ": " + (e.InnerException?.Message ?? e.Message));
            }
        }
        Console.WriteLine("tests " + tests.Count + "  failed " + failed);
        return failed == 0 ? 0 : 1;
    }
}
