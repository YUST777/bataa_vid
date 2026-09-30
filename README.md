# Bataa commercial ("Built while you watch")

24 s seamless loop, 1920x1080 @ 30 fps. A screen recording of Bataa guiding a user in the real Blender UI, then the
Bataa duck breaks out of the monitor through a liquid-glass surface into a 3D room that builds itself, and dives
back into the screen.

Latest shots: `review/ad3d/00_storyboard.png`.

## Timeline
| Time | Frames | Source |
|---|---|---|
| 0:00 - 0:07 | 2D 0-209 | `scripts/screen2d.py` (real Blender UI captures + Bataa panel + pet sprites) |
| 0:07 - 0:24 | 3D 1-510 | `assets/ad_scene.blend`, built by `scripts/build_ad3d.py` |

## Rebuild from scratch (Linux, Blender 5.2)
```sh
# 1. restore the Free Standard desk pack (needs a Sketchfab API token in ~/.sketchfab_token)
python3 scripts/sk_get.py 0e5bbf1098aa41fdb1e78b301d7b1d7d
# 2. 2D screen segment -> screen_frames/
python3 scripts/screen2d.py
# 3. 3D scene -> assets/ad_scene.blend   (scripts/nvb = headless Blender on the NVIDIA GPU)
scripts/nvb -P scripts/build_ad3d.py
# 4. review stills
scripts/nvb -P scripts/test_frames.py -- 1 14 20 90 300 424 510
```
Scripts use absolute paths under `/home/yousefmsm1/Desktop/blender/bataa_ad`. Clone to that path or update `ROOT`.

## Pipeline scripts
- `duck_retopo.py`: builds the clean, editable quad duck (`assets/bataa_v2.blend`) using the Hyper3D mesh (`assets/ai_duck/base.obj`) only as a shape reference
- `duck_rig_v2.py`, `duck_sprites.py`: control rig and the premium 2D pet sprites (`sprites/`)
- `menu_layers.py`: cuts the real Blender Add/Mesh menus out of internal screenshots (`ui_caps/`)
- `tiktok_page.py`: bataa.app TikTok screen for the phone
- `ph_get.py`, `sk_get.py`, `sk_search.py`: Poly Haven / Sketchfab asset tools

## Still to do
Blender-UI reveal (0:14-0:19), sound design (ElevenLabs), final render + encode.

## Credits
- "Monstera Deliciosa Potted Mid-Century plant" by ChubbyPanda (Sketchfab, CC BY 4.0): see `assets/sketchfab/1ab9bf841df04c07b1819be596327629/CREDIT.txt`
- "Computer Workspace Pack - FREE" by manix3d (Sketchfab, Free Standard): not included, downloaded by `sk_get.py`
- Poly Haven models, textures and HDRIs: CC0
- Inter font: SIL Open Font License
