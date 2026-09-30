#!/usr/bin/env bash
# vast.ai: one command from a fresh Ubuntu + NVIDIA image (e.g. "nvidia/cuda:12.x-runtime-ubuntu22.04").
#   export SKETCHFAB_TOKEN=...            # needed once to fetch the desk pack (not redistributable)
#   bash vast/setup_and_render.sh         # renders all 510 3D frames on every GPU, then encodes
# Re-running is safe: finished frames are skipped.
set -euo pipefail
BL_VER=5.2.2
WORK=/home/yousefmsm1/Desktop/blender          # scripts use this absolute path
REPO=https://github.com/YUST777/bataa_vid.git

apt-get update -qq && apt-get install -y -qq git wget xz-utils ffmpeg python3-pip \
  libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 libgl1 libegl1 >/dev/null
pip3 install -q pillow numpy fonttools

mkdir -p "$WORK" && cd "$WORK"
[ -d bataa_ad/.git ] || git clone -q "$REPO" bataa_ad
cp -n bataa_ad/assets/bataa.png "$WORK/bataa.png"
if [ ! -x "/opt/blender-$BL_VER/blender" ]; then
  wget -q "https://download.blender.org/release/Blender${BL_VER%.*}/blender-$BL_VER-linux-x64.tar.xz" -O /tmp/bl.txz
  tar -xf /tmp/bl.txz -C /opt && mv "/opt/blender-$BL_VER-linux-x64" "/opt/blender-$BL_VER"
fi
BL="/opt/blender-$BL_VER/blender"
cd bataa_ad

# assets that are not in git
if [ ! -f assets/sketchfab/0e5bbf1098aa41fdb1e78b301d7b1d7d/scene.gltf ]; then
  : "${SKETCHFAB_TOKEN:?set SKETCHFAB_TOKEN to download the desk pack}"
  python3 scripts/sk_get.py 0e5bbf1098aa41fdb1e78b301d7b1d7d
fi
# 2D segment + the screen textures the 3D scene needs
[ -f screen_frames/s_0209.png ] || python3 scripts/screen2d.py
# 3D scene
[ -f assets/ad_scene.blend ] || "$BL" -b --factory-startup --python-exit-code 1 -P scripts/build_ad3d.py

# one Blender per GPU on the same range; placeholders make them share the work
NGPU=$(nvidia-smi -L | wc -l)
echo "rendering on $NGPU GPU(s)"
for i in $(seq 0 $((NGPU - 1))); do
  CUDA_VISIBLE_DEVICES=$i "$BL" -b assets/ad_scene.blend --factory-startup --python-exit-code 1 \
    -P scripts/render_final.py -- --start 1 --end 510 > "renders/log_gpu$i.txt" 2>&1 &
  sleep 20          # stagger start so the processes do not claim the same first frames
done
wait
bash vast/encode.sh
echo "DONE -> renders/bataa_ad.mp4"
