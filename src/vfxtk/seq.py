"""Image sequence discovery and frame-range helpers shared by every tool.

Understands the usual VFX naming conventions:

    beauty.1001.exr          (dot-separated frame number)
    beauty_1001.exr          (underscore-separated)
    beauty.####.exr          (hash padding)
    beauty.%04d.exr          (printf padding)
    beauty.1001-1100#.exr    (range + hash)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_EXTS = {
    ".exr", ".dpx", ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".tga",
    ".hdr", ".bmp", ".webp", ".psd", ".cin", ".sxr",
}

# head, frame digits, tail (extension included)
_FRAME_RE = re.compile(r"^(?P<head>.*?[._-]?)(?P<frame>-?\d+)(?P<tail>\.[^.]+)$")
_HASH_RE = re.compile(r"(?P<hash>#+|@+)")
_PRINTF_RE = re.compile(r"%0?(?P<pad>\d*)d")


@dataclass
class Sequence:
    directory: Path
    head: str
    tail: str
    padding: int
    frames: list[int] = field(default_factory=list)

    # -- naming -----------------------------------------------------------
    @property
    def name(self) -> str:
        return f"{self.head}{'#' * self.padding}{self.tail}"

    @property
    def printf(self) -> str:
        return str(self.directory / f"{self.head}%0{self.padding}d{self.tail}")

    def path(self, frame: int) -> Path:
        if self.padding == 0:
            return self.directory / self.head
        num = f"{abs(frame):0{self.padding}d}"
        if frame < 0:
            num = "-" + num
        return self.directory / f"{self.head}{num}{self.tail}"

    def paths(self) -> list[Path]:
        return [self.path(f) for f in self.frames]

    # -- frame range ------------------------------------------------------
    @property
    def first(self) -> int:
        return self.frames[0]

    @property
    def last(self) -> int:
        return self.frames[-1]

    @property
    def missing(self) -> list[int]:
        have = set(self.frames)
        return [f for f in range(self.first, self.last + 1) if f not in have]

    @property
    def is_single(self) -> bool:
        return len(self.frames) == 1 and self.padding == 0

    def range_str(self) -> str:
        return compress_frames(self.frames)

    def __len__(self) -> int:
        return len(self.frames)


def compress_frames(frames: list[int]) -> str:
    """[1,2,3,5,7,8] -> '1-3,5,7-8'"""
    if not frames:
        return ""
    frames = sorted(set(frames))
    out, start, prev = [], frames[0], frames[0]
    for f in frames[1:]:
        if f == prev + 1:
            prev = f
            continue
        out.append(f"{start}" if start == prev else f"{start}-{prev}")
        start = prev = f
    out.append(f"{start}" if start == prev else f"{start}-{prev}")
    return ",".join(out)


def parse_frames(spec: str) -> list[int]:
    """'1001-1010,1020,1030-1040x5' -> list of frames."""
    frames: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        step = 1
        if "x" in part:
            part, s = part.split("x", 1)
            step = int(s)
        m = re.match(r"^(-?\d+)(?:-(-?\d+))?$", part)
        if not m:
            raise ValueError(f"bad frame spec: {part!r}")
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        frames.extend(range(a, b + 1, step))
    return frames


def _is_image(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTS


def scan_dir(directory: Path, include_singles: bool = True) -> list[Sequence]:
    """Group every image in a directory into sequences."""
    groups: dict[tuple[str, str, int], list[int]] = {}
    singles: list[str] = []
    for entry in sorted(os.listdir(directory)):
        if entry.startswith(".") or not _is_image(entry):
            continue
        m = _FRAME_RE.match(entry)
        if not m:
            singles.append(entry)
            continue
        digits = m.group("frame").lstrip("-")
        pad = len(digits) if digits.startswith("0") or len(digits) > 1 else 1
        key = (m.group("head"), m.group("tail"), pad)
        groups.setdefault(key, []).append(int(m.group("frame")))

    seqs = []
    for (head, tail, pad), frames in groups.items():
        seqs.append(Sequence(directory, head, tail, pad, sorted(frames)))

    # merge padding variants that are really one sequence (e.g. 999 and 1000)
    merged: dict[tuple[str, str], Sequence] = {}
    for s in sorted(seqs, key=lambda s: s.padding):
        k = (s.head, s.tail)
        if k in merged and merged[k].padding <= s.padding and all(
            len(str(abs(f))) >= merged[k].padding for f in s.frames
        ):
            merged[k].frames = sorted(set(merged[k].frames) | set(s.frames))
        else:
            merged.setdefault(k, s)
    seqs = sorted(merged.values(), key=lambda s: s.name)

    if include_singles:
        for name in singles:
            seqs.append(Sequence(directory, name, "", 0, [0]))
    return seqs


def resolve(target: str | Path) -> list[Sequence]:
    """Turn a user argument into sequences.

    Accepts a directory, a single frame of a sequence, a single image, or a
    pattern using #### / %04d / @@@@.
    """
    target = str(target)
    p = Path(target).expanduser()

    if p.is_dir():
        return scan_dir(p)

    hash_m = _HASH_RE.search(p.name)
    printf_m = _PRINTF_RE.search(p.name)
    if hash_m or printf_m:
        if hash_m:
            head, tail = p.name[: hash_m.start()], p.name[hash_m.end():]
        else:
            head, tail = p.name[: printf_m.start()], p.name[printf_m.end():]
        # strip a "1001-1100" range written just before the hashes
        head = re.sub(r"\d+-\d+$", "", head)
        matches = [
            s for s in scan_dir(p.parent, include_singles=False)
            if s.head == head and s.tail == tail
        ]
        if not matches:
            raise FileNotFoundError(f"no frames found for {target}")
        return matches

    if p.is_file():
        m = _FRAME_RE.match(p.name)
        if m:
            for s in scan_dir(p.parent, include_singles=False):
                if s.head == m.group("head") and s.tail == m.group("tail") and int(
                    m.group("frame")
                ) in s.frames:
                    return [s]
        return [Sequence(p.parent, p.name, "", 0, [0])]

    raise FileNotFoundError(target)


def single(seq: Sequence) -> Path:
    """Path for a Sequence that wraps a lone file (padding 0)."""
    return seq.directory / seq.head
