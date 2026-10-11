# Masonry structural audit — 2026-10-11

Prepared for Astra with Codex (GPT-6). The visual goal is believable pale masonry: upright courses on walls, coherent joints around curved surfaces, and real openings through the wall geometry.

## Results

The same reusable Unity Unicorn checker compared the original source commit `aaf38001588f837bc448007367775694b3883fcd` with the repaired working tree. The final source audit completed at **2026-10-11 13:40:28 America/Denver** (19:40:28 UTC).

| Check | Original | Repaired |
|---|---:|---:|
| Mesh buffers valid | 209 / 209 | 209 / 209 |
| Blocked opening/recess sample segments | 58 / 58 | 0 / 58 |
| Blocked assembled clerestory junction segments | 4 / 4 | 0 / 4 |
| Masonry triangles blending conflicting projection grids | 7,438 | 0 |
| Exact same-facing duplicate triangles | 4 | 0 |
| Exposed coplanar overlap candidates | 248 | 0 |
| Entire black texture rows | 2 | 0 |
| Duplicate layout placements | 0 | 0 |
| Error / warning / informational groups | 9 / 20 / 3 | 0 / 0 / 3 |

The three remaining notes describe 36 overlapping downward faces beneath verified closed, opaque Floor cuboids. These are covered construction contacts. The checker retains their evidence rather than labeling them exposed visual defects.

## Repairs

- Replaced blended triplanar mortar grids on Wall/Stone materials with authored, metric surface coordinates. Flat walls use upright courses; barrel vaults follow their circumference and length; arch rings use radial joints; exterior domes use continuous meridians and a periodic closing seam. Unjointed decorative marble retains its existing material treatment.
- Corrected reflected sideways arch cutters and three inward-facing circular window cutters. A signed-volume guard catches future inverted closed cutters. The repaired geometry includes the aqueduct's eight through arches, arcade windows/recesses, nave recesses, the pump doorway and round clerestories.
- Continued the central vestibule round windows through the neighboring Nave end caps. Both east/west openings are tested in the assembled layout and inspected at window height in Unity.
- Turned arcade arch frames into the room and embedded their backs slightly in the wall. Added masonry surrounds where plain openings previously had wall courses running directly into the arch edge.
- Removed redundant gallery end/cap side faces and corrected the dome flange/roof-ring joint. Curved soffits remain intact.
- Rebuilt all Wall texture channels using complete periodic coordinates. The old integer division painted only 2,046 of 2,048 rows. The normal map keeps the existing PNG-to-Unity tangent convention.

All 15 masonry modules retain their bounding boxes and ordered material slots. Their combined triangle count changed from 194,107 to 250,648, mainly from explicit arch surrounds in the distant wings. This adds geometry; headset frame time has not been measured in this audit.

## Reusable tools

The [Unity Unicorn source](https://github.com/findastra/unity-unicorn) contains `scripts/masonry-structural-audit-20261011.py` and `scripts/run-unity-tool-20261011.py`. The auditor uses Python's standard library, reads the project without launching Unity, can compare a `--git-ref` snapshot without checking it out, and writes a dated report plus optional usage receipt.

The local private tool library records source paths, requirements, evidence and last completed use. Failed attempts remain separate. Its dates come from actual execution records; imports, app launches and copying commands never advance them. Existing cloud tools and avatar workflows have historical dates when supported by records, otherwise Unknown.

The repair tools in this repository are:

1. `ArtSource/gen/rebuild-wall-textures-20261011.py`: rebuild the three existing Wall textures with NumPy and Pillow; `--check` verifies periodic coverage.
2. `ArtSource/gen/regenerate-masonry-20261011.py`: run in Blender with `--background --python-exit-code 1 --python` and `-- --apply`. It stages and checks all 15 modules before replacing existing mesh bytes, preserving original dated backups. Without `--apply`, it does not replace project mesh data.
3. **Piranesi → Refresh Masonry and Capture Audit**: refresh existing Unity mesh assets in place, enable the authored mapping on masonry materials, open the saved scene, compile/render its shader variants, and capture ten inspection views. It preserves asset GUIDs and does not rebuild or save the scene layout. It emits a completion/failure receipt that Unity Unicorn can import.

## Validation and boundaries

The generator's 57 aperture/recess/control checks passed. The independent auditor validates buffer integrity, authored UV availability, material opt-in, planar overlaps, source frame orientation, texture rows and duplicate layout placements. It checks 58 individual-module sample segments and four assembled central clerestory junction segments against seven intersecting placed modules. Its 21 regression tests and the foreground recorder's seven tests pass. Passing sparse probes does not certify every point in an opening.

Unity 2022.3.22f1 imported the project and the masonry shader without compilation errors. The final ten-view run completed at 13:37:29 America/Denver. The saved scene was rendered for inspection; private dated logs, mesh backups, images and usage receipts remain in ignored local audit folders. The editor refresh preserves the saved scene's existing references and reimports updated meshes before rendering, because copying their serialized data alone left stale render buffers in an earlier inspection.

No VRChat upload, multiplayer test, headset performance test or complete player-clearance sweep is claimed. Cross-module intersections outside the sampled views, collider behavior and decorative objects remain separate review areas. These checks concern the virtual world's masonry appearance and mesh construction.

## Recovery

The original source is retained at the commit above and original mesh bytes are backed up locally before replacement. Restore a matching set of generator sources, mesh bytes, generated Unity meshes, material settings, shader and Wall textures when rolling back; do not mix authored-mapping materials with legacy placeholder UV meshes.

## GitHub Goldfish naming check

The saved repository-scoped naming correction was exercised again against current Markdown. Corrected text produced no naming finding; a deliberately mistaken example produced one. The private feedback rule and report remain outside Git. Whole-account link/profile findings from this single-repository snapshot are not evidence about those other repositories. Existing non-masonry findings in the October 8 GitHub audit remain separate work.
