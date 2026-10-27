# Far Hall Quests and dead ends: no save lost to an early find (20261026)

- **What changed:** `HouseQuest` (the Far Hall Quests) and `HouseStorm` (the five dead ends) wrote to PlayerData on every
  find, even before the player's save had arrived, and `OnPlayerRestored` then replaced what was in memory with the save.
  VRChat's docs say to wait for `OnPlayerRestored` before reading or writing PlayerData, because an early write "may be
  overwritten when the persistent data is received". So a prize or dead end found in the first moments of a visit was
  lost (the save wins), or the earlier visits' progress was lost (the early write wins). Now both scripts save nothing
  until the save arrives, then merge the early finds into it and save the merged set once. An early fifth dead end still
  brings the storm; a returning player who already has 5 / 5 gets no storm just for arriving, as before.
- **Tests:** `Tests/HouseSave/` compiles the real `HouseQuest`, `HouseQuestLink`, `HouseStorm` and `HouseStormLink` against
  stand-ins (`Shims.cs`, outside `Assets/`, so Unity never sees it) and runs 11 headless tests:
  `dotnet run -c Release` from that folder (.NET 8, no packages). Before the fix 7 of 11 failed; after it all pass.
- **Not checked here:** the UdonSharp compile, ClientSim and a real upload (Astra's PC).
- **Astra's words and date:** "the Cung List" (2026-10-26), item 1 (Udon kit library). The kit library found this bug
  (findastra/unity-unicorn PR #32, `changes/udon-kits-20261026.md`) and named HouseQuest as likely to have it.
- **Model:** Claude Opus 5.5 (`claude-opus-5-5`), 2026-10-26. Branch `claude/housequest-save-fix-20261026`.
