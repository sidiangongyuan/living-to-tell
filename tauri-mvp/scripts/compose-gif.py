"""Compose tutorial GIFs from a JSON frame manifest.

The recorder writes a manifest with ordered PNG frames and per-frame durations.
This helper keeps GIF generation reproducible without requiring ffmpeg.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def contain(image: Image.Image, max_width: int) -> Image.Image:
    if image.width <= max_width:
        return image
    ratio = max_width / image.width
    height = int(image.height * ratio)
    return image.resize((max_width, height), Image.Resampling.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-width", type=int, default=960)
    args = parser.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    frames = []
    durations = []
    for item in data["frames"]:
        frame = contain(Image.open(item["path"]).convert("RGB"), args.max_width)
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
        durations.append(int(item.get("duration", 1200)))

    if not frames:
        raise SystemExit("No frames found in manifest.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    first, rest = frames[0], frames[1:]
    first.save(
        args.output,
        save_all=True,
        append_images=rest,
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == "__main__":
    main()
