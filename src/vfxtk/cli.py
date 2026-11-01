"""`vfxtk` - list the tools and check the environment."""

from __future__ import annotations

import shutil
import sys

from .common import ocio_config, out

TOOLS = {
    "seqinfo": "frame ranges, missing/corrupt frames, res, channels, size",
    "layers": "list / extract AOVs from (multi-part) EXRs",
    "contact": "contact sheet of a folder or sequence",
    "exr2proxy": "colour-managed movie from an image sequence",
    "ocio-convert": "batch colour space / format conversion, .tx textures",
    "usdinfo": "USD stats, prim tree, dependencies, missing references",
    "vidprep": "ffmpeg recipes: HAP, ProRes, social crops, GIFs, frames",
}


def doctor() -> int:
    ok = True

    def check(name, fn):
        nonlocal ok
        try:
            detail = fn()
            out.print(f"  [green]ok[/]   {name} {detail or ''}")
        except Exception as e:  # noqa: BLE001
            ok = False
            out.print(f"  [red]fail[/] {name}: {e}")

    def oiio_v():
        import OpenImageIO as o
        return o.VERSION_STRING

    def ocio_v():
        import PyOpenColorIO as o
        cfg = o.Config.CreateFromFile(ocio_config())
        return f"{o.__version__} ({cfg.getName()})"

    def usd_v():
        from pxr import Usd
        return ".".join(map(str, Usd.GetVersion()))

    def binary(b):
        def f():
            p = shutil.which(b)
            if not p:
                raise RuntimeError("not on PATH")
            return p
        return f

    out.print("[bold]vfxtk doctor[/]")
    check("python", lambda: sys.version.split()[0])
    check("OpenImageIO", oiio_v)
    check("OpenColorIO", ocio_v)
    check("USD", usd_v)
    check("ffmpeg", binary("ffmpeg"))
    check("ffprobe", binary("ffprobe"))
    return 0 if ok else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "doctor":
        raise SystemExit(doctor())
    out.print("[bold]vfxtk[/] - run any tool with -h\n")
    for name, desc in TOOLS.items():
        out.print(f"  [cyan]{name:<13}[/] {desc}")
    out.print("\n  [cyan]vfxtk doctor[/]  check libraries and binaries")


if __name__ == "__main__":
    main()
