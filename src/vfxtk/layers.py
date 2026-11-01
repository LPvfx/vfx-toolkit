"""layers - list and extract AOVs from (multi-part) EXRs.

    layers beauty.1001.exr                       list layers
    layers beauty.####.exr -e diffuse -o out/    extract one layer, every frame
    layers beauty.1001.exr -e diffuse,specular   extract several
    layers beauty.####.exr --split -o aovs/      every layer to its own sequence
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path

from rich.table import Table

from .common import console, die, oiio, out
from .seq import resolve

RGBA_ORDER = {"R": 0, "G": 1, "B": 2, "A": 3, "X": 0, "Y": 1, "Z": 2, "U": 0, "V": 1}


def layer_map(path: str) -> "OrderedDict[str, list[tuple[int, int, str]]]":
    """layer name -> [(subimage, channel index, full channel name)]"""
    OIIO = oiio()
    inp = OIIO.ImageInput.open(path)
    if not inp:
        die(OIIO.geterror())
    layers: "OrderedDict[str, list]" = OrderedDict()
    sub = 0
    while inp.seek_subimage(sub, 0):
        spec = inp.spec()
        part = spec.get_string_attribute("name")
        for i, ch in enumerate(spec.channelnames):
            if "." in ch:
                layer = ch.rsplit(".", 1)[0]
            elif part and sub > 0:
                layer = part
            else:
                layer = "rgba" if ch in ("R", "G", "B", "A") else ch
            layers.setdefault(layer, []).append((sub, i, ch))
        sub += 1
    inp.close()
    return layers


def _short(ch: str) -> str:
    return ch.rsplit(".", 1)[-1]


def extract(path: str, layer: str, chans: list, dest: Path):
    OIIO = oiio()
    subs = {s for s, _, _ in chans}
    if len(subs) != 1:
        die(f"layer {layer} spans multiple parts - not supported")
    sub = subs.pop()
    src = OIIO.ImageBuf(path, sub, 0)
    ordered = sorted(chans, key=lambda c: RGBA_ORDER.get(_short(c[2]).upper(), 9))
    idx = tuple(c[1] for c in ordered)
    names = tuple(_short(c[2]) for c in ordered)
    buf = OIIO.ImageBufAlgo.channels(src, idx, newchannelnames=names)
    if buf.has_error:
        die(buf.geterror())
    dest.parent.mkdir(parents=True, exist_ok=True)
    buf.specmod().attribute("compression", src.spec().get_string_attribute("compression") or "zip")
    if not buf.write(str(dest)):
        die(buf.geterror())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="layers", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="EXR file, frame or pattern")
    ap.add_argument("-e", "--extract", help="comma-separated layer names to extract")
    ap.add_argument("--split", action="store_true", help="extract every layer")
    ap.add_argument("-o", "--out", default=".", help="output folder (default: here)")
    args = ap.parse_args(argv)

    seq = resolve(args.target)[0]
    first = str(seq.path(seq.first))
    layers = layer_map(first)

    if not args.extract and not args.split:
        t = Table(header_style="bold", title=seq.name)
        t.add_column("layer")
        t.add_column("part")
        t.add_column("channels")
        for name, chans in layers.items():
            t.add_row(name, str(chans[0][0]), " ".join(_short(c[2]) for c in chans))
        out.print(t)
        return

    wanted = list(layers) if args.split else [x.strip() for x in args.extract.split(",")]
    unknown = [w for w in wanted if w not in layers]
    if unknown:
        die(f"unknown layer(s): {', '.join(unknown)}. Have: {', '.join(layers)}")

    outdir = Path(args.out)
    frames = seq.frames
    with console.status("extracting") as st:
        for f in frames:
            src = seq.path(f)
            for layer in wanted:
                safe = layer.replace("/", "_")
                if seq.padding:
                    name = f"{seq.head.rstrip('._')}_{safe}.{f:0{seq.padding}d}.exr"
                else:
                    name = f"{Path(seq.head).stem}_{safe}.exr"
                dest = outdir / safe / name if args.split else outdir / name
                st.update(f"{layer} {f}")
                extract(str(src), layer, layers[layer], dest)
    console.print(f"[green]done[/] {len(wanted)} layer(s) x {len(frames)} frame(s) -> {outdir}")


if __name__ == "__main__":
    main()
