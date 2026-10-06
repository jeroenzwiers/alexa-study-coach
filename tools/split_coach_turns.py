"""Cuts each coach clip into its verdict and the question that follows it.

A coach line closes the previous turn and opens the next in one breath - "That's
right. Question 3. Where do most of the cell's chemical reactions take place?" -
and spoken as one utterance the verdict lands against the question after it
rather than the answer it judges. The page plays the two halves with a beat
between, which needs them as two files.

No new recording: the halves are cut out of the clip that is already there, and
the boundary is found the same way the pack was split in the first place - cut
finely, then group by how long each half ought to take from its word count.
Thresholding the pause cannot work, because the pause inside a sentence and the
pause between sentences are the same length.

    python tools/split_coach_turns.py

Writes one file per half, named by the hash the page looks for. Leaves the whole
clip in place, so a half that cannot be cut falls back to it.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import importlib.util

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIO = ROOT / "preview" / "audio"

spec = importlib.util.spec_from_file_location("pack", ROOT / "tools" / "split_audio_pack.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)

QUESTION_START = re.compile(r"\s(?=Question \d+\.)")


def audio_key(text: str) -> str:
    """The page's hash, FNV-1a over the sentence, as eight hex digits."""
    h = 0x811C9DC5
    for ch in text:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def main() -> int:
    manifest = json.loads((AUDIO / "manifest.json").read_text(encoding="utf-8"))
    cut = kept = 0
    for entry in manifest:
        if entry["role"] != "coach":
            continue
        match = QUESTION_START.search(entry["text"])
        if not match:
            continue
        verdict = entry["text"][: match.start()]
        question = entry["text"][match.start() + 1 :]
        source = AUDIO / entry["file"]
        if not source.exists():
            continue

        spans = pack.cut_points(source, 0.20, -40)
        grouped = pack.group_segments(spans, [len(verdict), len(question)])
        halves = grouped[0] if isinstance(grouped, tuple) else grouped
        if halves is None or len(halves) != 2:
            kept += 1
            print(f"  could not cut: {verdict[:48]}")
            continue

        for (begin, end), text in zip(halves, (verdict, question)):
            target = AUDIO / f"{audio_key(text)}.mp3"
            subprocess.run(
                [pack.tool("ffmpeg"), "-hide_banner", "-loglevel", "error",
                 "-ss", f"{begin:.3f}", "-to", f"{end:.3f}", "-i", str(source),
                 "-c:a", "libmp3lame", "-b:a", "192k", str(target), "-y"],
                check=True,
            )
        cut += 1

    print(f"{cut} coach lines cut in two" + (f", {kept} left whole" if kept else ""))
    print("The page falls back to the whole line wherever a half is missing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
