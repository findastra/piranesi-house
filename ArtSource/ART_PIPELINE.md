# The House: Art Pipeline

How we get from "procedural first pass" to "insanely good". Everything in v1 is generated, so every
pass below can replace one layer at a time without breaking the world.

```
ArtSource/gen/*.py  ──►  Assets/Piranesi/{Textures,Audio,Meshes,Data}  ──►  Piranesi ▸ Build House  ──►  Scene
     (Blender + numpy)          (committed, rebuildable)                      (Unity editor)
```

## 0. What exists now (v1)

| Layer | How it's made | File |
|---|---|---|
| Architecture kit (vestibules, sail vaults, colonnaded naves, stone arcades, columns, plinths, lanterns, sea gate, distant wings) | Blender (bpy) procedural modelling, booleans, analytic coffer AO in vertex colour | `gen/kit.py`, `Blender/House_Kit.blend` |
| Statues | Public 3D scans → oriented, scaled, decimated (16k / 3k LOD), Cycles-baked AO | `gen/statues.py` |
| Layout (maze, statue placement, lights, shafts, particles, sounds, probes) | Seeded generator | `gen/layout.py` |
| PBR textures (4 marbles, inlaid floor, ashlar, sand, water normals, caustics, particle atlas) | Spectral (FFT) tileable noise | `gen/textures.py`, `gen/caustics.py` |
| Sound (marble/sand/water footsteps, ocean, wind, cascade, house drone, season shimmer) | Synthesised | `gen/audio.py` |
| Shaders | Hand-written BIRP (triplanar stone, ocean, sky, shafts, particles…) | `Assets/Piranesi/Shaders` |

## 1. Hero statues: the book's cast

Each statue in `STATUE_REGISTRY.md` gets replaced in order of importance. Three routes, best first:

1. **Real museum scans (free, no-copyright).** Search *Scan the World* (MyMiniFactory), *Three D Scans*,
   Smithsonian 3D, Sketchfab "CC0 / CC-BY museum". Fauns, gorillas, elephants, chess players,
   cymbal players and beehive bearers all exist as classical or Victorian sculptures.
   - Import into Blender → `Remesh (voxel 4 mm)` → `Decimate` to 40k → bake normal map from the full scan
     onto the 40k mesh → export 16k LOD0 / 3k LOD1 with the normal map. Run `gen/statues.py` style AO bake.
2. **Sculpt from a reference sheet (ChatGPT desktop).** Ask ChatGPT for a turnaround sheet
   ("front / side / back orthographic views of a classical white-marble statue of a faun with a finger
   to its lips, neutral lighting, plain background"). Use it as Blender background images, block out with
   the Skin modifier + metaballs, then sculpt (Dyntopo → Multires) at 2–5M polys, retopo/decimate and bake.
3. **Kitbash.** Combine scan parts (torso + head + drapery) in Blender, fuse with voxel remesh, sculpt seams.

Marble look: the `Piranesi/Stone` shader is triplanar, so statues need **no UVs**. Baked AO goes in vertex
colour (R). For hero pieces add a baked normal map: that's the single biggest quality jump.

## 2. Architecture detail passes (Blender)

- **Corinthian capitals:** replace the procedural bell with a real acanthus capital (sculpt one leaf,
  array ×8 radially ×2 rows, add volutes + abacus). Bake normals onto the low-poly capital.
- **Coffers:** add rosettes in each coffer (one sculpted rosette, instanced via Geometry Nodes on coffer centres).
- **Friezes:** sculpt a 2 m tileable relief strip (garlands, ox skulls, waves) → bake to a normal + AO trim sheet.
- **Weathering:** Geometry Nodes edge-wear mask → vertex colour G; the shader can use it for chipped edges.
- **Lightmap UVs:** when we bake GI, each module gets UV2 (Smart UV Project, 0.02 margin) from Blender.

## 3. Lighting quality

1. **Now:** realtime sun/moon with soft shadows, trilight ambient driven by the clock, box-projected
   reflection probes, bloom + ACES grading, fake volumetric shafts, caustics.
2. **Next:** bake *indirect* light from the lanterns and the sky (Progressive GPU, ~25 texels/m) and keep
   sun/moon realtime. This adds bounce light and contact AO to the halls.
3. **Later:** day/night probe sets swapped by the clock; LTCGI or area-light reflections for the windows.

## 4. Textures

- Upgrade the generated marbles with real CC0 scans (Poly Haven / ambientCG marble, travertine, sand)
  at 2K. Keep the same filenames (`MarbleWhite_Albedo.png` etc.) and re-run *Build House*.
- ChatGPT is good for **inscription tablets and painted ceilings**: generate the art, then turn it into
  height/normal in Materialize or Blender.

## 5. Sound

Replace synthesised clips with recorded CC0 sets (same filenames):
marble footsteps (hard soles on stone), sand, wading; real surf at a rocky shore; wind in colonnades;
gulls/albatross for the sea gate. Keep loops 30–60 s and seamless.

## 6. The book's halls (scene list)

Each becomes a dedicated room built from the kit plus bespoke hero pieces:

- First Vestibule (Minotaurs). TO CONFIRM
- The Drowned Halls (lower level, permanently flooded, colossal heads in sand)
- The Upper Halls (clouds drifting through, birds)
- The Ninth Northern Hall
- The Eighth Vestibule. TO CONFIRM
- The Alcove of the Dead (handled with care, low-key)
- Specific statue halls (Faun, Gorilla, Woman carrying a beehive, Elephant carrying a castle,
  two Kings playing chess, Boy with cymbals, angel caught in a rose bush)

Anything marked *TO CONFIRM* needs a check against the book before we build it. We do not
reproduce the novel's text; any writing in the world is original.

## 7. Performance budget (PC VR)

- ≤ 2.5M visible tris at worst view (statue LODs + occlusion culling: run *Piranesi ▸ Bake Occlusion Culling*).
- ≤ 6 realtime pixel lights affecting any object; lanterns are point lights without shadows.
- One GrabPass (the sea). Texture memory ≈ 250 MB at 2K BC7.
- Quest/Android version later: separate lightweight shaders, baked lighting, 1K textures, fewer statues.
