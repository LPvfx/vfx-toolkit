"""seqinfo - what's in this folder / sequence?

    seqinfo renders/                 every sequence in the folder
    seqinfo beauty.####.exr          one sequence
    seqinfo shot.1001.exr --check    also open every frame to find corrupt ones
    seqinfo renders/ --json          machine readable
"""

from __future__ import annotations

import argparse
import json

from rich.table import Table

from .common import console, die, human_bytes, oiio, out
from .seq import Sequence, compress_frames, resolve


def describe(seq: Sequence, check: bool = False) -> dict:
    OIIO = oiio()
    first = seq.path(seq.first)
    info: dict = {
        "name": seq.name,
        "directory": str(seq.directory),
        "pattern": seq.printf if seq.padding else str(first),
        "frames": seq.range_str() if seq.padding else "-",
        "first": seq.first if seq.padding else None,
        "last": seq.last if seq.padding else None,
        "count": len(seq),
        "missing": compress_frames(seq.missing) if seq.padding else "",
        "missing_count": len(seq.missing) if seq.padding else 0,
    }
    size = 0
    for p in seq.paths():
        try:
            size += p.stat().st_size
        except OSError:
            pass
    info["size"] = size

    inp = OIIO.ImageInput.open(str(first))
    if not inp:
        info["error"] = OIIO.geterror() or "could not open"
        return info
    spec = inp.spec()
    subimages = 0
    while inp.seek_subimage(subimages, 0):
        subimages += 1
    inp.close()

    info.update(
        width=spec.width,
        height=spec.height,
        full=f"{spec.full_width}x{spec.full_height}",
        data_window=f"{spec.x},{spec.y} {spec.width}x{spec.height}",
        channels=spec.nchannels,
        channel_names=list(spec.channelnames),
        dtype=str(spec.format),
        compression=spec.get_string_attribute("compression"),
        subimages=subimages,
        fps=spec.get_string_attribute("FramesPerSecond"),
        colorspace=spec.get_string_attribute("oiio:ColorSpace"),
    )

    if check and seq.padding:
        bad = []
        for f in seq.frames:
            buf = OIIO.ImageBuf(str(seq.path(f)))
            if not buf.read(force=True) or buf.has_error:
                bad.append(f)
        info["corrupt"] = compress_frames(bad)
        info["corrupt_count"] = len(bad)
    return info


def main(argv=None):
    ap = argparse.ArgumentParser(prog="seqinfo", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="folder, frame, or pattern (####, %%04d)")
    ap.add_argument("--check", action="store_true", help="fully read every frame to find corrupt files")
    ap.add_argument("--json", action="store_true", help="output JSON")
    ap.add_argument("--channels", action="store_true", help="list every channel name")
    args = ap.parse_args(argv)

    results = []
    for t in args.targets:
        try:
            seqs = resolve(t)
        except FileNotFoundError as e:
            die(f"not found: {e}")
        for s in seqs:
            with console.status(f"reading {s.name}"):
                results.append(describe(s, check=args.check))

    if args.json:
        out.print_json(json.dumps(results))
        return

    table = Table(show_lines=False, header_style="bold")
    for col in ("sequence", "frames", "#", "missing", "res", "ch", "type", "compression", "size"):
        table.add_column(col, overflow="fold")
    if args.check:
        table.add_column("corrupt")

    for r in results:
        if "error" in r:
            table.add_row(r["name"], r["frames"], str(r["count"]), "", f"[red]{r['error']}[/]", "", "", "", "")
            continue
        missing = f"[red]{r['missing']}[/]" if r["missing"] else "[green]none[/]"
        if r["frames"] == "-":
            missing = ""
        row = [
            r["name"], r["frames"], str(r["count"]), missing,
            f"{r['width']}x{r['height']}", str(r["channels"]),
            r["dtype"], r["compression"] or "", human_bytes(r["size"]),
        ]
        if args.check:
            row.append(f"[red]{r.get('corrupt')}[/]" if r.get("corrupt") else "[green]ok[/]")
        table.add_row(*row)
    out.print(table)

    if args.channels:
        for r in results:
            if "channel_names" in r:
                out.print(f"[bold]{r['name']}[/] ({r['subimages']} subimage(s)): " + ", ".join(r["channel_names"]))


if __name__ == "__main__":
    main()
