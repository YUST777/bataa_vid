#!/usr/bin/env bash
# 2D (210 frames) + 3D (510 frames) -> 24 s seamless loop. Adds audio/mix.wav if present.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p renders/seq
i=0
for f in screen_frames/s_*.png renders/3d/f_*.png; do
  ln -sf "$(realpath "$f")" "renders/seq/$(printf '%05d' $i).png"; i=$((i + 1))
done
AUDIO=(); [ -f audio/mix.wav ] && AUDIO=(-i audio/mix.wav -c:a aac -b:a 256k -shortest)
# master: high-quality H.264 that social platforms re-encode cleanly
ffmpeg -y -v error -framerate 30 -i renders/seq/%05d.png "${AUDIO[@]}" \
  -c:v libx264 -preset slow -crf 14 -profile:v high -pix_fmt yuv420p -movflags +faststart renders/bataa_ad.mp4
# vertical 9:16 cut for TikTok / Reels / Shorts (centre crop, 1080x1920)
ffmpeg -y -v error -i renders/bataa_ad.mp4 -vf "scale=-2:1920,crop=1080:1920" -c:v libx264 -preset slow -crf 16 \
  -pix_fmt yuv420p -c:a copy -movflags +faststart renders/bataa_ad_vertical.mp4
echo "frames: $i"
