# Beyond the Edge: video generation package

A 15 s, 16:9, 4K cinematic spot of a black Porsche 911 GT3 RS. It cruises a mountain pass at golden hour, then loses control and goes over a cliff.

## Recommended render settings

| Model (Higgsfield) | Settings | Est. cost |
|---|---|---|
| **Kling 3.0** (`kling3_0`): best value, native multi-shot + audio | duration 15, mode `4k`, aspect 16:9, sound on | **90 credits** |
| Seedance 2.5 (`seedance_2_5`): strongest physics/realism | duration 15, resolution `4k`, aspect 16:9, audio on, mode `t2v` | 420 credits |

HazeGen alternative: `seedance-25` at `4k` (prices listed per clip, plus extra for 4K/length).

---

## Single-prompt version (paste as-is)

```
Photorealistic live-action Hollywood car commercial, shot on a professional cinema camera with anamorphic lenses, 2.39-style widescreen feel in 16:9, natural golden-hour sunlight, dark cinematic teal-and-orange grade, subtle film grain, horizontal anamorphic lens flares. Five shots, hard cuts:

SHOT 1 (0-3s): Wide aerial drone shot gliding over a winding mountain road carved into a rocky ridge at golden hour; a single black Porsche 911 GT3 RS with its large rear wing carves through the S-bends, long shadows, warm low sun, hazy valley below.

SHOT 2 (3-6s): Rapid macro B-roll montage: a forged center-lock wheel spinning with motion-blurred road behind it, red brake caliper glowing; titanium exhaust tips shimmering with heat haze; LED headlight snapping on; close detail of the flat-six engine intake and carbon bodywork with sunlight sliding across the glossy black paint.

SHOT 3 (6-9s): Low-angle tracking shot inches above the asphalt, camera car alongside, the Porsche accelerating hard toward a sharp cliffside hairpin, guardrail and sheer drop visible ahead, road texture streaking past.

SHOT 4 (9-12s): Real-time slows to dramatic slow motion: the rear steps out, tires smoke, the car slides sideways, smashes through the metal roadside barrier in a burst of sparks, debris and gravel, and tips nose-first over the cliff edge. Empty cabin, no visible driver. Realistic weight, momentum and metal deformation.

SHOT 5 (12-15s): Epic aerial follow shot as the car falls away down the cliff face into a vast golden valley, dust trailing; the camera pulls up and back into a sweeping wide landscape of mountains and sunset haze, ending on a still, majestic wide frame.

Audio: realistic high-revving Porsche flat-six engine and gear shifts, tire screech, metal impact, rushing wind, swelling cinematic orchestral score that drops to near-silence at the moment of the fall, then a final low orchestral hit.
```

**Negative prompt:**
```
animation, cartoon, anime, video game graphics, CGI look, plastic render, unrealistic physics, floating car, morphing car shape, warped wheels, extra wheels, distorted logos, text, subtitles, watermark, people, gore, low resolution, flicker
```

---

## Per-shot version (if a model handles single shots better)

Render each as a 3 s clip (or 5 s and trim), same style suffix on all:

> *Style suffix:* `photorealistic live-action, cinema camera, anamorphic lens, golden hour, dark teal-and-orange grade, film grain, 16:9, 4K`

1. `Wide aerial drone shot of a black Porsche 911 GT3 RS driving along a winding mountain road at golden hour, long shadows, hazy valley below.`
2. `Macro close-ups: spinning forged wheel with red brake caliper, heat haze from titanium exhaust, LED headlight turning on, sunlight gliding across glossy black carbon bodywork.`
3. `Low-angle tracking shot just above the asphalt as a black Porsche 911 GT3 RS accelerates hard toward a sharp cliffside hairpin bend.`
4. `Slow motion: the black Porsche loses traction, slides sideways, crashes through a metal roadside barrier in a shower of sparks and debris, and tips over the cliff edge. No driver visible, realistic physics.`
5. `Aerial follow shot of the car falling away into a vast golden valley, camera rising into an epic wide sunset landscape of mountains.`

Then cut together at 3 s each and lay one continuous audio bed (engine → screech/impact → wind → orchestral swell) across all five.

---

## Notes

- **Brand filters:** some models flag real brand names. If a render comes back `ip_detected`, swap "Porsche 911 GT3 RS" for *"a black rear-engined German sports coupé with a tall swan-neck rear wing"*.
- **Crash continuity** is the hardest part. If shot 4 looks off, generate it alone with a start frame taken from the end of shot 3.
- Keep the cabin empty / driver unseen so the crash stays clean.
