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
  libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 libgl1 libegl1 libglvnd0 libopengl0 >/dev/null
pip3 install -q pillow numpy fonttools

PROFILE=${PROFILE:---eevee}         # --eevee (minimal, ~minutes) | --fast (Cycles) | "" (Cycles max quality)
# EEVEE needs the NVIDIA OpenGL/EGL driver inside the container: rent with env NVIDIA_DRIVER_CAPABILITIES=all
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
mkdir -p "$WORK" && cd "$WORK"
[ -d bataa_ad/.git ] || git clone -q "$REPO" bataa_ad
cp -n bataa_ad/assets/bataa.png "$WORK/bataa.png"
if [ ! -x "/opt/blender-$BL_VER/blender" ]; then
  wget -q "https://download.blender.org/release/Blender${BL_VER%.*}/blender-$BL_VER-linux-x64.tar.xz" -O /tmp/bl.txz
  tar -xf /tmp/bl.txz -C /opt && mv "/opt/blender-$BL_VER-linux-x64" "/opt/blender-$BL_VER"
fi
BL="/opt/blender-$BL_VER/blender"
cd bataa_ad
mkdir -p renders screen_frames

# assets that are not in git
if [ ! -f assets/sketchfab/0e5bbf1098aa41fdb1e78b301d7b1d7d/scene.gltf ]; then
  : "${SKETCHFAB_TOKEN:?set SKETCHFAB_TOKEN to download the desk pack}"
  python3 scripts/sk_get.py 0e5bbf1098aa41fdb1e78b301d7b1d7d
fi
# only the 2 screen textures the 3D scene needs, then the full 2D segment on the CPU while the GPUs render
[ -f screen_frames/screen_after.png ] || python3 -c "import sys; sys.argv=['x']; sys.path.insert(0,'scripts'); import screen2d as s; s.frame(0, with_pet=False).save('screen_frames/screen_start.png'); s.frame(s.N-1, with_pet=False).save('screen_frames/screen_after.png')"
( [ -f screen_frames/s_0209.png ] || python3 scripts/screen2d.py > renders/log_2d.txt 2>&1 ) &
PID2D=$!
# 3D scene
[ -f assets/ad_scene.blend ] || "$BL" -b --factory-startup --python-exit-code 1 -P scripts/build_ad3d.py

# one Blender per GPU on the same range; placeholders make them share the work
NGPU=$(nvidia-smi -L | wc -l)
echo "rendering on $NGPU GPU(s)"
for i in $(seq 0 $((NGPU - 1))); do
  CUDA_VISIBLE_DEVICES=$i "$BL" -b assets/ad_scene.blend --factory-startup --python-exit-code 1 \
    -P scripts/render_final.py -- --start 1 --end 510 $PROFILE > "renders/log_gpu$i.txt" 2>&1 &
  sleep 8           # stagger start so the processes do not claim the same first frames
done
wait
wait $PID2D 2>/dev/null || true
bash vast/encode.sh
echo "DONE -> renders/bataa_ad.mp4"
