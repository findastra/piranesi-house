# The House: a VRChat world inspired by *Piranesi*

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
  Scripts/     HouseClock (day, seasons, tide, sky, fog, snow, particles), HouseFootsteps
  Shaders/     Stone (triplanar marble + caustics + snow), Ocean, Sky, LightShaft, Particle, …
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
python ArtSource/gen/layout.py
```
Copy the outputs into `Assets/Piranesi/` and run **Build House** again.

## Credits and licences

Statue stand-ins are research scans and must be replaced before any public release; see
`ArtSource/STATUE_REGISTRY.md`. All textures, sounds, and code here are original procedural work.
Inspired by Susanna Clarke's *Piranesi*. This is an unofficial fan work and does not reproduce the
novel's text.
