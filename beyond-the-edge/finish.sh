#!/usr/bin/env bash
# Final finishing pass: upscale, teal/orange grade, vignette, grain, 2.39:1 letterbox,
# end title, mux soundtrack.
# Usage: finish.sh <frames_dir> <audio.wav> <out.mp4> [width] [height]
set -euo pipefail
FRAMES=$1; AUDIO=$2; OUT=$3; W=${4:-1920}; H=${5:-1080}
BAR=$(python3 -c "print(round(($H - $W/2.39)/2))")
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf
[ -f "$FONT" ] || FONT=$(fc-list : file | head -1 | cut -d: -f1)
VF="scale=${W}:${H}:flags=lanczos,\
colorbalance=rs=-0.12:gs=-0.02:bs=0.10:rm=-0.07:gm=-0.01:bm=0.05:rh=0.06:gh=0.01:bh=-0.07,\
eq=contrast=1.08:saturation=1.0:gamma=1.04,\
curves=master='0/0.025 0.2/0.21 0.5/0.55 0.8/0.84 1/0.97',\
vignette=angle=PI/4.6,\
noise=alls=7:allf=t,\
drawbox=x=0:y=0:w=iw:h=${BAR}:color=black:t=fill,\
drawbox=x=0:y=ih-${BAR}:w=iw:h=${BAR}:color=black:t=fill,\
drawtext=fontfile=${FONT}:text='BEYOND THE EDGE':fontcolor=white:fontsize=h/14:x=(w-text_w)/2:y=(h-text_h)/2:\
alpha='if(lt(t,13.3),0,if(lt(t,14.1),(t-13.3)/0.8,1))':shadowcolor=black@0.6:shadowx=2:shadowy=2,\
fade=t=in:st=0:d=0.4,fade=t=out:st=14.55:d=0.45"
ffmpeg -y -loglevel error -framerate 24 -i "$FRAMES/f_%04d.png" -i "$AUDIO" \
  -vf "$VF" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 256k -shortest "$OUT"
echo "wrote $OUT"
