"""Shared bits: colour config, console output, image helpers."""

from __future__ import annotations

import os
import shutil
import sys

from rich.console import Console

console = Console(stderr=True)
out = Console()

# OCIO 2.2+ ships built-in configs, so nothing needs downloading.
# $OCIO wins if set (e.g. a show config); otherwise the ACES CG config.
DEFAULT_CONFIG = "ocio://default"


def ocio_config() -> str:
    return os.environ.get("OCIO", DEFAULT_CONFIG)


def die(msg: str, code: int = 1) -> "None":
    console.print(f"[bold red]error:[/] {msg}")
    sys.exit(code)


def need(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        die(f"{binary} not found on PATH (brew install {binary})")
    return path


def oiio():
    try:
        import OpenImageIO as _oiio
    except ImportError:
        die("OpenImageIO python module missing - run ./bootstrap.sh")
    return _oiio


def guess_colorspace(path: str, spec) -> str:
    """Best guess at an input file's colour space.

    Float/half EXRs are assumed scene-linear (ACEScg); everything else is
    assumed display-referred sRGB. Override with --from on any tool.
    """
    declared = spec.get_string_attribute("oiio:ColorSpace")
    if declared and declared.lower() not in ("", "linear", "scene_linear"):
        return declared
    fmt = str(spec.format)
    if path.lower().endswith((".exr", ".hdr", ".sxr")) or fmt in ("half", "float"):
        return "ACEScg"
    return "sRGB Encoded Rec.709 (sRGB)"


def load_rgb(path: str, layer: str | None = None):
    """Read an image as an RGB float ImageBuf (first part, or a named layer)."""
    OIIO = oiio()
    buf = OIIO.ImageBuf(path)
    spec = buf.spec()
    names = list(spec.channelnames)
    if layer:
        idx = [i for i, n in enumerate(names) if n.rsplit(".", 1)[0] == layer]
        if not idx:
            die(f"{path}: no layer '{layer}'")
    else:
        idx = [names.index(c) for c in ("R", "G", "B") if c in names]
        if not idx:
            idx = list(range(min(3, spec.nchannels)))
    if len(idx) == 1:
        idx = idx * 3
    idx = idx[:3]
    rgb = OIIO.ImageBufAlgo.channels(buf, tuple(idx), newchannelnames=("R", "G", "B"))
    if rgb.has_error:
        die(rgb.geterror())
    # bring the data window to the display window (overscan/crops)
    full = spec.full_width, spec.full_height
    if (spec.x, spec.y, spec.width, spec.height) != (spec.full_x, spec.full_y, *full):
        rgb = OIIO.ImageBufAlgo.crop(rgb, OIIO.get_roi_full(spec))
    return rgb, spec


def to_display(buf, src_space: str, display: str | None, view: str | None):
    """Scene/encoded colour -> display-ready via an OCIO display/view."""
    OIIO = oiio()
    cfg = ocio_config()
    cc = OIIO.ColorConfig(cfg)
    display = display or cc.getDefaultDisplayName()
    view = view or cc.getDefaultViewName(display)
    res = OIIO.ImageBufAlgo.ociodisplay(buf, display, view, src_space, colorconfig=cfg)
    if res.has_error:
        die(f"OCIO: {res.geterror()}")
    return res


def resize_to(buf, width: int | None = None, height: int | None = None):
    OIIO = oiio()
    spec = buf.spec()
    if not width and not height:
        return buf
    if width and not height:
        height = max(1, round(spec.height * width / spec.width))
    elif height and not width:
        width = max(1, round(spec.width * height / spec.height))
    width += width % 2  # video encoders want even sizes
    height += height % 2
    return OIIO.ImageBufAlgo.resize(buf, roi=OIIO.ROI(0, width, 0, height, 0, 1, 0, 3))


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"
