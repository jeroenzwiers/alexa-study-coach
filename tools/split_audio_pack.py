"""Cuts three long recordings into the 33 clips the demo page asks for.

Rendering 33 lines one at a time is 33 downloads and 33 renames. Instead paste
`preview/audio/lines-<role>.txt` into the speech engine in one go - the blank
lines between sentences become pauses - save the result as
`preview/audio/<role>.mp3`, and run this. It finds the pauses, cuts there, and
names each piece with the hash the page will look for.

    python tools/split_audio_pack.py                 # all three roles
    python tools/split_audio_pack.py narrator        # just one

It refuses to write anything if a role does not split into exactly the number
of lines the manifest expects, and says what it found instead - a silent gap
missed or invented would shift every clip after it onto the wrong sentence,
which is worse than not splitting at all. If that happens, raise --gap (the
engine paused less than expected) or lower it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIO = ROOT / "preview" / "audio"

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


def duration(path: pathlib.Path) -> float:
    out = subprocess.run(
        [tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def silences(path: pathlib.Path, gap: float, floor: int) -> list[tuple[float, float]]:
    out = subprocess.run(
        [tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path),
         "-af", f"silencedetect=noise={floor}dB:d={gap}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    spans, start = [], None
    for line in out.stderr.splitlines():
        m = re.search(r"silence_start: ([0-9.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([0-9.]+)", line)
        if m and start is not None:
            spans.append((start, float(m.group(1))))
            start = None
    return spans


def cut_points(path: pathlib.Path, gap: float, floor: int) -> list[tuple[float, float]]:
    """Speech spans, from the gaps between them."""
    total = duration(path)
    quiet = silences(path, gap, floor)
    spans, position = [], 0.0
    for begin, end in quiet:
        if begin - position > 0.25:          # not a pause inside a sentence
            spans.append((position, begin))
        position = end
    if total - position > 0.25:
        spans.append((position, total))
    return spans


def split(role: str, manifest: list[dict], gap: float, floor: int) -> bool:
    source = AUDIO / f"{role}.mp3"
    if not source.exists():
        print(f"  {role:9} no {source.name} yet - skipped")
        return True

    wanted = [m for m in manifest if m["role"] == role]
    spans = cut_points(source, gap, floor)
    if len(spans) != len(wanted):
        print(f"  {role:9} FOUND {len(spans)} pieces, EXPECTED {len(wanted)} - nothing written")
        print(f"            try --gap {gap / 2:.2f} if the engine paused less,"
              f" or --gap {gap * 1.5:.2f} if it pauses inside sentences")
        return False

    for span, entry in zip(spans, wanted):
        begin, end = span
        target = AUDIO / entry["file"]
        subprocess.run(
            [tool("ffmpeg"), "-hide_banner", "-loglevel", "error",
             "-ss", f"{begin:.3f}", "-to", f"{end:.3f}", "-i", str(source),
             "-c:a", "libmp3lame", "-b:a", "192k", str(target), "-y"],
            check=True,
        )
    print(f"  {role:9} {len(wanted)} clips written")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roles", nargs="*", default=None)
    parser.add_argument("--gap", type=float, default=0.45,
                        help="seconds of quiet that counts as a break between lines")
    parser.add_argument("--floor", type=int, default=-40,
                        help="dB below which audio counts as quiet")
    args = parser.parse_args()

    path = AUDIO / "manifest.json"
    if not path.exists():
        sys.exit("No manifest. Run: node tools/dump_demo_speech.mjs")
    manifest = json.loads(path.read_text(encoding="utf-8"))

    roles = args.roles or sorted({m["role"] for m in manifest})
    ok = all(split(role, manifest, args.gap, args.floor) for role in roles)
    print()
    print("The page uses whatever is there and falls back to the browser voice")
    print("for the rest, so a partial pack is fine.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
