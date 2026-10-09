# Piranesi House

A VRChat world inspired by Susanna Clarke's *Piranesi*.

An endless labyrinth of marble halls, thousands of statues, and a sea that rises and falls through it all.
Built for PC VRChat (Unity 2022.3.22f1, VRChat Worlds SDK 3.10, UdonSharp).

## What's in it (v1)

- **The labyrinth:** a 3×3 grid of domed vestibules (coffered sail vaults, an oculus open to the sky)
  linked by colonnaded naves (Corinthian columns, gilded cornice, coffered barrel vault) and stone
  arcades (niches, stepped plinths, lanterns). Missing links are walled with colossal statues.
- **The tide:** one sea fills the whole House, from dry floors at low tide to knee-deep at high tide.
  It has turquoise refraction, reflections, caustics on the submerged marble, a wet line that dries
  slowly, splashing footsteps, and a Sea Gate where steps descend into open ocean.
- **Time:** day/night with a moon and stars, plus four seasons (spring petals, summer motes, autumn
  leaves, winter snow and frost). Everything is driven from VRChat server time, so everyone in an
  instance sees the same sky.
- **Atmosphere:** volumetric-style light shafts that follow the sun, dust sparkles, a cascade
  pouring from a high window, mica glints in the marble, bloom and ACES grading, reverb per hall.
- **Sound:** marble, sand, and water footsteps, surf, wind in the oculi, the House's low drone.

## What's new in v2

- **The Colossus:** a 13 m robed figure stands in the north-central hall with one enormous hand raised palm-up
  under the oculus. A spotlight from the oculus always falls on the palm, and sparkles drift around it.
  *Rest in the Colossus' palm* (interact at the pedestal) seats you in the hand, in the light.
- **Window seats:** every outward-facing wall now has a great arched window. Each window bay holds a marble
  seat between mullioned panes, with 80 seats in total across the vestibules and the six perimeter arcades.
- **Islands instead of the 'show' wings:**
  - **South Beach:** coconut palms, hibiscus, beach grass, shells and starfish, crabs that scuttle away
    from you, a hammock, a dock and a gondola.
  - **Ruin Isle:** a roofless colonnade whose fallen columns lie across the capitals overhead, draped in ivy,
    with hammocks slung between the columns. A garden table is laid with fruit, brass goblets and a candelabra,
    and a chess game sits on a broken drum.
  - **Pump Isle:** a stone pump house and a turning water wheel (noria) that lifts the sea into an
    aqueduct. The aqueduct carries it into the House, where it pours as the cascade.
  - **Albatross Isle (easter egg):** a beached Venetian long canoe with an albatross on her nest, among
    shells and starfish.
- **Gondolas:** five rowable boats at the Sea Gate, the new East Water Stair, and the island docks.
  Sit in the stern to row (move forward/back, turn to steer). Boats ride the live tide, stop at walls,
  and ground softly on beaches. Open water is chest-deep, so you can always wade.
- **Stair tower and water slide:** a helical stair climbs 27 m from the south hall to a roof pavilion. The
  flume corkscrews down to the south beach. Everyone in the instance sees the rider.
- **Reefs:** about 860 coral colonies, sponges, clams and starfish ring the House and the islands, made from
  museum coral scans tinted to living colours. A Dutch ship lies wrecked on the reef with her masts out of
  the water.
- **Wildlife:** dolphins pass now and then, leaping three times. The schedule is synced to server time.
- **Ivy:** climbing and cascading English ivy grown on the actual walls, columns, tower and aqueduct, with
  vines hanging into the oculi and veiling the water-stair arches.

## Opening it

1. Open the project in Unity 2022.3.22f1 (via VRChat Creator Companion).
2. Menu **Piranesi ▸ Build House**. This generates meshes, materials, and the scene, then bakes the
   reflection probes. It takes a few minutes the first time.
3. **Piranesi ▸ Time, Season & Tide Preview** scrubs the clock in the editor.
4. Press Play (ClientSim) to walk around, or use the VRChat SDK panel to build and test.
5. Optional: **Piranesi ▸ Bake Occlusion Culling** before uploading.

## Layout

```
Assets/Piranesi/
  Scripts/     HouseClock (day, seasons, tide, sky, fog, snow, particles), HouseFootsteps,
               HouseSeat, HouseBoat, HouseSlide, HouseCrabs, HouseDolphins, HouseSpinner
  Shaders/     Stone (triplanar marble + caustics + snow), Ocean, Sky, LightShaft, Particle,
               Prop, Foliage, Coral, WaterFlow, Glass, …
  Imported/    scanned props and their packed textures (Albedo / Normal / Mask)
  Editor/      HouseBuilder (Build House), HousePreviewWindow
  Textures/ Audio/ Meshes/ Data/   generated source data (rebuildable from ArtSource)
  Generated/   created by Build House (meshes, materials, probes)
  Scenes/      PiranesiHouse.unity
ArtSource/
  gen/         Python + Blender generators for every asset
  Blender/     House_Kit.blend (all architecture modules)
  ART_PIPELINE.md, STATUE_REGISTRY.md
```

## Regenerating art

```
pip install bpy==5.2.2 numpy scipy pillow trimesh fast-simplification
python ArtSource/gen/textures.py && python ArtSource/gen/caustics.py
python ArtSource/gen/audio.py
python ArtSource/gen/kit.py          # Blender architecture kit
python ArtSource/gen/statues.py      # needs ArtSource/src/*.obj scans
python ArtSource/gen/assets.py       # downloads in assets/: Poly Haven, Smithsonian, ambientCG
python ArtSource/gen/nature.py       # palms, hibiscus, grass
python ArtSource/gen/kit2.py         # window walls, islands, gondola, hammock, table, aqueduct, tower, slide
python ArtSource/gen/creatures.py    # dolphin, albatross, nest
python ArtSource/gen/colossus.py     # needs ArtSource/src/mh (MakeHuman CC0 base mesh)
python ArtSource/gen/ivy.py          # grows the ivy on the generated architecture
python ArtSource/gen/lods.py         # distant LODs for heavy props
python ArtSource/gen/layout.py       # also writes the v2 world (world2.py)
python ArtSource/gen/manifest_u.py
```
Copy the outputs into `Assets/Piranesi/` and run **Build House** again.

## Credits and licences

Statue stand-ins are research scans and must be replaced before any public release; see
`ArtSource/STATUE_REGISTRY.md`. The architecture, stone textures, sounds and code are original procedural
work. v2 adds free CC0 assets:

- [Poly Haven](https://polyhaven.com): fruit, tableware, candelabra, lantern, chest, plants, rocks and
  surface textures such as planks, linen, palm bark, sand and marble (CC0).
- [ambientCG](https://ambientcg.com): ivy leaf scans (LeafSet017, LeafSet029), foliage, rope and marble
  (CC0).
- [Smithsonian Open Access](https://www.si.edu/openaccess): coral, sponge, sea star, clam, cone shell and
  crab scans (CC0).
- [MakeHuman](http://www.makehumancommunity.org): base mesh and skeleton for the Colossus (CC0).
Inspired by Susanna Clarke's *Piranesi*. This is an unofficial fan work and does not reproduce the
novel's text.
