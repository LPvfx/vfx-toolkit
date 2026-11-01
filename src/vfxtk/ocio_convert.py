"""ocio-convert - batch colour space / format conversion.

    ocio-convert --spaces                                   list colour spaces
    ocio-convert plates/*.exr --from ACEScg --to "Linear Rec.709 (sRGB)" -o lin709/
    ocio-convert shot.####.exr --to "sRGB Encoded Rec.709 (sRGB)" --ext png -o pngs/
    ocio-convert shot.####.exr --display "sRGB - Display" --view "ACES 2.0 - SDR 100 nits (Rec.709)" --ext jpg -o review/
    ocio-convert textures/ --to ACEScg --ext exr --tx       textures -> ACEScg .tx (mipmapped)

Uses $OCIO if set, otherwise OCIO's built-in ACES CG config.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .common import console, die, guess_colorspace, ocio_config, oiio, out
from .seq import resolve

DTYPE_FOR_EXT = {".exr": "half", ".png": "uint16", ".jpg": "uint8", ".jpeg": "uint8",
                 ".tif": "uint16", ".tiff": "uint16", ".dpx": "uint10", ".tx": "half"}


def list_spaces():
    import PyOpenColorIO as OCIO
    cfg = OCIO.Config.CreateFromFile(ocio_config())
    out.print(f"[bold]{cfg.getName()}[/]  ({ocio_config()})\n")
    out.print("[bold]colour spaces[/]")
    for cs in cfg.getColorSpaces():
        fam = cs.getFamily()
        out.print(f"  {cs.getName():<36} [dim]{fam}[/]")
    out.print("\n[bold]displays / views[/]")
    for d in cfg.getDisplays():
        out.print(f"  {d}")
        for v in cfg.getViews(d):
            out.print(f"      {v}")
    out.print("\n[bold]roles[/]")
    for role, cs in cfg.getRoles():
        out.print(f"  {role:<20} {cs}")


def convert_one(src: Path, dest: Path, args):
    OIIO = oiio()
    cfg = ocio_config()
    buf = OIIO.ImageBuf(str(src))
    if buf.has_error:
        return f"{src}: {buf.geterror()}"
    space = args.src or guess_colorspace(str(src), buf.spec())
    # formats other than EXR/TX can't hold AOVs: keep just RGB(A)
    if dest.suffix.lower() not in (".exr", ".tx"):
        names = list(buf.spec().channelnames)
        keep = [names.index(c) for c in ("R", "G", "B", "A") if c in names] or list(
            range(min(3, len(names))))
        if len(keep) != len(names):
            buf = OIIO.ImageBufAlgo.channels(buf, tuple(keep))
    if args.display:
        cc = OIIO.ColorConfig(cfg)
        view = args.view or cc.getDefaultViewName(args.display)
        res = OIIO.ImageBufAlgo.ociodisplay(buf, args.display, view, space, colorconfig=cfg)
    elif args.to:
        res = OIIO.ImageBufAlgo.colorconvert(buf, space, args.to, colorconfig=cfg)
    else:
        res = buf
    if res.has_error:
        return f"{src}: {res.geterror()}"
    ext = dest.suffix.lower()
    if ext in DTYPE_FOR_EXT:
        res.set_write_format(DTYPE_FOR_EXT[ext])
    if ext == ".exr":
        res.specmod().attribute("compression", args.compression)
    if ext not in (".exr", ".hdr", ".tx"):
        res = OIIO.ImageBufAlgo.clamp(res, 0.0, 1.0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if args.tx:
        ok = OIIO.ImageBufAlgo.make_texture(OIIO.MakeTxTexture, res, str(dest.with_suffix(".tx")))
        return None if ok else f"{src}: {OIIO.geterror()}"
    if not res.write(str(dest)):
        return f"{src}: {res.geterror()}"
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ocio-convert", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--spaces", action="store_true", help="list colour spaces, displays, views")
    ap.add_argument("--from", dest="src", help="input space (default: guessed per file)")
    ap.add_argument("--to", help="output colour space")
    ap.add_argument("--display", help="apply a display/view instead of --to")
    ap.add_argument("--view")
    ap.add_argument("--ext", help="output format, e.g. exr png jpg tif (default: same)")
    ap.add_argument("--compression", default="dwaa", help="EXR compression (default dwaa)")
    ap.add_argument("--tx", action="store_true", help="write mipmapped .tx textures")
    ap.add_argument("-o", "--out", required=False, help="output folder")
    ap.add_argument("-j", "--jobs", type=int, default=8)
    args = ap.parse_args(argv)

    if args.spaces:
        list_spaces()
        return
    if not args.targets:
        ap.error("give files/folders/patterns, or --spaces")
    if not (args.to or args.display or args.ext or args.tx):
        ap.error("nothing to do - give --to, --display, --ext or --tx")
    if not args.out:
        ap.error("-o/--out is required (never overwrites sources)")

    outdir = Path(args.out)
    jobs = []
    for t in args.targets:
        for s in resolve(t):
            for p in s.paths():
                ext = f".{args.ext.lstrip('.')}" if args.ext else p.suffix
                jobs.append((p, outdir / (p.stem + ext)))

    errors = []
    with console.status(f"converting {len(jobs)} file(s)"):
        with ThreadPoolExecutor(args.jobs) as pool:
            for err in pool.map(lambda j: convert_one(j[0], j[1], args), jobs):
                if err:
                    errors.append(err)
    for e in errors:
        console.print(f"[red]{e}[/]")
    console.print(f"[green]done[/] {len(jobs) - len(errors)}/{len(jobs)} -> {outdir}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
