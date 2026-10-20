# Open arches audit — 2026-10-11

Piranesi House now has open wall arches instead of glazed windows. Architectural panes and window bars are removed. Circular and rectangular high wall windows become arched openings; existing open roof oculi remain unchanged. Low exterior arches reach the floor. All 80 old window-seat interactions are removed from the saved scene and generator layout.

The aqueduct bed follows the existing water ribbon instead of burying its outlet. Its retaining walls rest on that slope without overlapping exposed end faces, the spout is below the stream, and the noria outlet is open. Three declared high-arch probe contacts are intentional aqueduct bed/retaining-wall supports; separate water-centerline checks verify the route.

The tower newel now sits at its stair center. This intentionally changes the tower's minimum forward bound from -1 m to -0.06 m; other ordered material slots and bounds are preserved. A sand drift intersecting a low arch has moved 3 m clear. Legacy asset IDs and empty material slots remain for saved renderer compatibility and contain no window geometry.

## Validation

- 209 mesh buffers, 15 architectural modules, 41 opening profiles.
- All 630 local and 2,116 assembled samples pass, including 504 low tidal-passage samples. Glazing and window-bar triangle counts are zero.
- Unity recooks 60 colliders and tests the same 2,116 segments in both directions: zero blocked segments, glass triangles or window seats.
- Independent masonry audit: zero errors, zero warnings, three informational covered-floor contacts.
- Regeneration contract: 57 checks pass. Unity imports and captures 13 views; exterior arcade, sea passage and high openings visually inspected.
- Previous source revision: the new auditor finds 409 issues, including 1,392 glass triangles and 612 bar triangles. Corrected source: zero findings.

## Reuse and limits

Reusable source: `scripts/no-windows-audit-tool-20261011.py` in [Unity Unicorn](https://github.com/findastra/unity-unicorn). Supply project, dated report and usage-receipt paths; add `--unity-probes` before running **Piranesi → Apply Open Arches and Capture Audit**. Reports and execution evidence stay in the ignored local audit directory and private Unicorn inventory.

Checks use declared geometry profiles, sampled rays and Unity collider evidence. They do not simulate fluid dynamics or certify every possible player path. Existing tide and stream animation is retained. No VRChat upload or headset test is claimed. Prepared with Codex (GPT-6).

## Chat closeout — 2026-10-20

State: READY_FOR_REVIEW. Implementer: Codex, GPT-6; implementation ownership released. Reviewer: unassigned. No recipient receipt or independent review is claimed.

### What I did

The masonry/open-arches implementation is preserved at `2440bddb1717903f518e9aa55013958b95c5ed8a` on `codex/masonry-audit-20261011`, in [pull request #1](https://github.com/findastra/piranesi-house/pull/1). Unity Unicorn's tool release is the immutable `v0.3.0-20261011` tag at `ce0d2eb811569ecdaedfc087b42ae8a387ada6f1`. The validation above was performed October 11; this closeout does not claim a new Unity run or change tool-use dates.

The later vine-tool installation and generated editor/settings changes are separate work, described by its October 19 handoff. They were preserved and excluded from this closeout commit. No new Unity process was started for this closeout.

### Next action and acceptance

Review the delivered implementation against the open-arch requirements and recorded validation, then record receipt and review findings here or on PR #1. Merge and VRChat publication remain separate actions. Photo-specific edits still require the promised ZIP. This record is delivery evidence, not reviewer acceptance or an uploaded world.