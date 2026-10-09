# Piranesi House: GitHub audit

Audited October 8, 2026 (America/Denver), by Codex (GPT-6).
Baseline: [d457eedc64b347398f0ef13bd3055892592a5cb2](https://github.com/findastra/piranesi-house/commit/d457eedc64b347398f0ef13bd3055892592a5cb2).

## Naming corrections

The canonical project name is **Piranesi House** and the repository is
[`findastra/piranesi-house`](https://github.com/findastra/piranesi-house).
The legacy repository URL redirects to this repository. A case-insensitive
search of all 2,229 tracked files, including text, metadata, and file paths,
found no remaining occurrences of the former project name at the baseline.
This search does not inspect lettering embedded in images or archived ZIPs.

The README and art-pipeline headings now use the full canonical name.
Unity's display name now reads **Piranesi House**. Existing scene paths,
script types, asset identifiers, and Unity GUIDs are preserved.

## GitHub findings

| Surface | Observed result |
| --- | --- |
| Repository | Private; canonical repository name already correct |
| Description | Describes a VRChat world inspired by the novel; no mistaken project name |
| Issues and pull requests | Zero open and zero closed at audit time |
| Automated validation | No tracked Actions workflows; GitHub shows its setup page |
| Releases | No GitHub Releases published at audit time |
| Topics | None; descriptive topics would improve discovery |
| Default branch | `master`; this is a naming convention, not evidence of a broken branch |
| Licensing | No project-root LICENSE; the existing statue registry documents unresolved stand-in asset rights |

No branch rename or new license was applied. The existing documentation's
asset-replacement work remains outstanding. Neither a source upload nor this
audit verifies a VRChat publication.

## Source review findings

These two findings follow from source inspection; they have not been reproduced
in Unity or a multiplayer VRChat session. No gameplay code was changed.

1. **P2: exiting the slide early can cause a later teleport.**
   `Assets/Piranesi/Scripts/HouseSlide.cs:80-90` completes a ride and teleports
   the local player even if the player has already exited or respawned.
   `riding` has no station-exit or respawn cancellation path.
   `Assets/Piranesi/Editor/HouseBuilder.cs:1245-1253` enables station exit and
   creates the station on a separate child object. Forward station events to
   the controller and cancel the ride on exit or respawn. Verify that a rider
   who leaves early remains at their chosen destination after the original
   ride duration. [VRChat event documentation](https://creators.vrchat.com/worlds/udon/graph/event-nodes/).

2. **P2: a disconnected slide rider can leave other players locked out.**
   `HouseSlide.cs:44` blocks non-owners while synchronized distance indicates
   an unfinished ride. After ownership transfers, the new owner's local
   `riding` state is false and no handler clears the synchronized distance.
   Reset abandoned ride state during ownership recovery. Verify with three
   players: disconnect the rider and confirm either remaining player can
   start the next ride without waiting for the new owner to interact first.
   [VRChat ownership documentation](https://creators.vrchat.com/worlds/udon/networking/ownership/).

## Goldfish feedback

GitHub Goldfish was run against a local snapshot of this repository's Markdown,
tracked file list, and browser-observed metadata. It found no error-level
findings. Its missing-license and missing-topic findings apply here. Its
account/profile findings do not apply to a single-repository snapshot, and its
`master` warning is only a convention warning.

The owner-approved naming correction is kept in a private, untracked local
rule file and can be saved in Goldfish's browser interface. Future corrections
should be recorded as repository-scoped rules and checked against both a
mistaken example and the corrected source. This is explicit saved feedback,
not automatic model training. Tokens and local audit records are not included
in this repository.

## Validation and pending input

The naming diff passes `git diff --check`. The new audit report uses the
owner's lowercase, hyphenated, dated filename convention. A full Unity build,
VRChat multiplayer test, image review, and public deployment were not performed.
The owner's new photo-edit ZIP is pending; older ZIP redlines were not treated
as instructions for this change.
