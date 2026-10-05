"""Builds the finished video from the frames and the clip pack.

`tools/record_demo.mjs` drives the page with every clip taking its real length,
writes a still each time something changes, and logs when each clip started.
This holds each still for exactly as long as the page held it, lays each clip
back at exactly the millisecond it played, and writes the result. Nothing is
stretched or nudged: both halves came off the same clock.

    node tools/record_demo.mjs
    python tools/mux_demo.py

Writes preview/study-coach-demo.mp4.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "preview"
AUDIO = PREVIEW / "audio"

CANDIDATES = [
    r"C:\Users\Jeroen\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin",
]


def tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for folder in CANDIDATES:
        candidate = pathlib.Path(folder) / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    sys.exit(f"{name} not found. Install it with: winget install --id Gyan.FFmpeg")


def main() -> int:
    timeline_path = PREVIEW / "timeline.json"
    if not timeline_path.exists():
        sys.exit("Record first: node tools/record_demo.mjs")
    data = json.loads(timeline_path.read_text(encoding="utf-8"))
    frames, clips = data["frames"], data["clips"]
    # End shortly after the last word, not whenever the recorder stopped
    # polling. The capture leaves several seconds of tail, and on a three-minute
    # limit those are the seconds that decide whether the close is watched.
    last = clips[-1]
    total = int(last["at"] + last["seconds"] * 1000 + 1200)

    missing = [c for c in clips if not (AUDIO / c["file"]).exists()]
    if missing:
        sys.exit(f"{len(missing)} clips in the timeline are not on disk")

    # Each still is held until the next one was taken; the last until the end.
    listing = []
    for index, frame in enumerate(frames):
        ends = frames[index + 1]["at"] if index + 1 < len(frames) else total
        listing.append(f"file '{pathlib.Path(frame['file']).as_posix()}'")
        listing.append(f"duration {max(ends - frame['at'], 1) / 1000:.3f}")
    # concat wants the last file named twice or it drops its duration.
    listing.append(f"file '{pathlib.Path(frames[-1]['file']).as_posix()}'")
    concat = PREVIEW / "frames.txt"
    concat.write_text("\n".join(listing), encoding="utf-8")

    # Two passes. One ffmpeg invocation doing 33 delayed inputs, a mix, loudness
    # normalisation and an x264 encode crashed outright, and a crash in a single
    # command tells you nothing about which half failed.
    track = PREVIEW / "audio-track.m4a"
    build = [tool("ffmpeg"), "-hide_banner", "-loglevel", "error"]
    for clip in clips:
        build += ["-i", str(AUDIO / clip["file"])]
    parts = []
    for index, clip in enumerate(clips):
        delay = int(round(clip["at"]))
        parts.append(
            f"[{index}:a]adelay={delay}|{delay},aformat=channel_layouts=stereo[a{index}]"
        )
    mix = "".join(f"[a{i}]" for i in range(len(clips)))
    # normalize=0 because amix otherwise divides every input by the number of
    # them, which would leave a 33-clip track almost silent.
    parts.append(f"{mix}amix=inputs={len(clips)}:normalize=0:dropout_transition=0[mixed]")
    parts.append("[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    build += ["-filter_complex", ";".join(parts), "-map", "[out]",
              "-t", f"{total / 1000:.3f}", "-c:a", "aac", "-b:a", "192k",
              str(track), "-y"]
    print(f"mixing {len(clips)} clips...")
    subprocess.run(build, check=True)

    target = PREVIEW / "study-coach-demo.mp4"
    mux = [tool("ffmpeg"), "-hide_banner", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", str(concat),
           "-i", str(track),
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
           "-r", "30", "-c:a", "copy",
           "-t", f"{total / 1000:.3f}", str(target), "-y"]
    print(f"encoding {len(frames)} stills over {total / 1000:.1f} s...")
    subprocess.run(mux, check=True)
    print(f"written: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
