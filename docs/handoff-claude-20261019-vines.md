# Handoff: Unity Unicorn's vine tool in Piranesi House (Claude, 2026-10-19)

status: READY_FOR_REVIEW. Installed and compiling. No vines grown here, and no hand-off tried in this world.

## What Astra asked

Install Unity Unicorn's **vine-spawn-with-trumpet-flowers** (findastra/unity-unicorn PR #18, merged) in her three worlds.
She allowed Piranesi House in chat on 2026-10-19. The real page-to-Unity hand-off was tried in Astra's Infinite Pole
(findastra/astras-infinite-pole PR #5).

## What I did

- Copied `Assets/UnityUnicorn/Editor/vine-spawn-with-trumpet-flowers-20261019.cs` from unity-unicorn `main` (1e96a41),
  unchanged. Unity made its `.meta` files.
- Opened the project in Unity 2022.3.22f1 (it was closed). It compiled with 0 `error CS`, and the editor assembly has
  the tool's types. Menu: Tools › Unity Unicorn › vine-spawn-with-trumpet-flowers. It knows this is Piranesi House
  from the folder name.
- `.gitignore`: added `/UnityUnicornReports/` and `/UnityUnicornInbox/`, so page jobs and usage receipts stay on the PC.
- The PR branch `claude/vine-spawn-20261019` is cut from `master`. Codex's `codex/masonry-audit-20261011` (PR #1) wasn't
  touched.

## What opening Unity changed in the live folder (not committed)

The live folder is on Codex's `codex/masonry-audit-20261011`. Opening Unity there:

- Re-saved 65 generated Udon assets (`Assets/Piranesi/Scripts/*.asset`, `Assets/SerializedUdonPrograms/`,
  `Assets/UdonSharp/UtilityScripts/`) with LF line endings. Their content is the same; `git diff` shows nothing for them.
- Changed two lines in ProjectSettings:
  - `EditorBuildSettings.asset`: the XR loader settings GUID;
  - `ProjectSettings.asset`: the iOS automatic graphics API flag.
- To put them back, close Unity, then run `git checkout -- Assets ProjectSettings`. The untracked `Assets/UnityUnicorn/`
  stays.

## Open

1. No vines grown and no page job tried in this world.
2. Known from the Pole: in a dark spot, leaves render nearly black (the shader lights leaves only with scene light). The
   vine window opens too narrow.

Made with Claude Opus 5.5 (`claude-opus-5-5`), 2026-10-19.
