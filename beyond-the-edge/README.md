# Beyond the Edge: Blender build

A 15-second, 16:9 cinematic of a black GT3 RS-style coupé on a golden-hour mountain pass. It loses control at a cliffside bend, smashes through the guardrail in slow motion, and falls into the valley. Everything is generated from code: no downloaded assets, models or textures.

| Time | Shot | Camera |
|---|---|---|
| 0–3 s | Wide drone glide along the winding cliff road | `Cam1_Drone`, 26 mm |
| 3–6 s | Macro montage: spinning wheel, exhaust tips, headlight snapping on, rear 3/4 with wing | `Cam2a–d`, 28–55 mm, shallow DOF |
| 6–9 s | Low-angle tracking; the car overtakes the camera and charges the bend | `Cam3_Low`, 22 mm |
| 9–12 s | Slow motion (0.28×): slide, barrier impact, sparks and debris, tips over the edge | `Cam4_Crash`, 24 mm |
| 12–15 s | Aerial follow of the fall, rising into a wide of the valley, river and peaks | `Cam5_Aerial`, 40→19 mm zoom |

## Files

- `build_scene.py` builds the whole `.blend`:
  - procedural terrain with a road-carved cliff, a winding road with painted lines, a W-beam guardrail with a breakaway section, about 20k instanced pines and a river
  - the car model and the scripted crash physics
  - sparks and debris, all eight cameras, the Nishita golden-hour sky, Cycles settings, and a compositor pass for haze and anamorphic streaks
- `make_audio.py` synthesizes the soundtrack, synced to the same speed ramps as the picture:
  - a flat-six engine with gear shifts and exhaust crackle
  - slow-motion pitch-down, tyre screech, impact, scrape and wind
  - a D-minor orchestral cue
- `finish.sh` does the final pass: upscale, teal/orange grade, vignette, grain, 2.39:1 letterbox bars, end title, and muxing the audio in.
- `prompt.md` is the text-to-video prompt package, for use with an AI video model instead.

## Reproduce

```bash
blender -b --python build_scene.py -- --out scene.blend --res 1280x720 --samples 10
blender -b scene.blend -o frames/f_#### -s 1 -e 360 -a     # ~20 s/frame on 4 CPU cores
python3 make_audio.py audio.wav                             # needs numpy + scipy
./finish.sh frames audio.wav beyond_the_edge.mp4 1920 1080
```

For a native 4K render, pass `--res 3840x2160 --samples 16` to the build step and `3840 2160` to `finish.sh`. On a CPU-only machine this takes roughly 12× longer, so a GPU is strongly recommended.
