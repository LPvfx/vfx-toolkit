"""contact - build a contact sheet.

    contact renders/                     first frame of every sequence/image in a folder
    contact shot.####.exr --every 10     every 10th frame of one sequence
    contact shot.####.exr -n 24          24 frames spread evenly across the range
    contact renders/ --layer diffuse     show an AOV instead of RGB
    contact renders/ -o sheet.jpg --cols 6 --width 320
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from .common import console, die, guess_colorspace, load_rgb, oiio, resize_to, to_display
from .seq import resolve


def pick_frames(frames: list[int], every: int | None, count: int | None) -> list[int]:
    if every:
        return frames[::every]
    if count and count < len(frames):
        step = (len(frames) - 1) / max(1, count - 1)
        return [frames[round(i * step)] for i in range(count)]
    return frames


def main(argv=None):
    ap = argparse.ArgumentParser(prog="contact", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+")
    ap.add_argument("-o", "--out", default="contact.jpg")
    ap.add_argument("--cols", type=int, default=0, help="columns (default: roughly square)")
    ap.add_argument("--width", type=int, default=384, help="thumbnail width")
    ap.add_argument("--every", type=int, help="every Nth frame of a sequence")
    ap.add_argument("-n", "--count", type=int, help="N frames spread across each sequence")
    ap.add_argument("--layer", help="EXR layer/AOV to show")
    ap.add_argument("--from", dest="src", help="input colour space (default: guessed)")
    ap.add_argument("--display", help="OCIO display")
    ap.add_argument("--view", help="OCIO view")
    ap.add_argument("--no-labels", action="store_true")
    ap.add_argument("--gap", type=int, default=8)
    args = ap.parse_args(argv)
    OIIO = oiio()

    items: list[tuple[str, str]] = []  # (path, label)
    for t in args.targets:
        for s in resolve(t):
            if not s.padding:
                items.append((str(s.path(0)), s.head))
                continue
            # a folder of sequences -> first frame each unless told otherwise
            frames = pick_frames(s.frames, args.every, args.count)
            if Path(t).is_dir() and not (args.every or args.count):
                frames = [s.first]
            items += [(str(s.path(f)), f"{s.head.rstrip('._')} {f}") for f in frames]
    if not items:
        die("nothing to put on the sheet")

    thumbs = []
    with console.status("rendering thumbnails") as st:
        for path, label in items:
            st.update(label)
            rgb, spec = load_rgb(path, args.layer)
            rgb = resize_to(rgb, width=args.width)
            space = args.src or guess_colorspace(path, spec)
            disp = to_display(rgb, space, args.display, args.view)
            thumbs.append((disp, label))

    th = max(t.spec().height for t, _ in thumbs)
    tw = args.width + args.width % 2
    label_h = 0 if args.no_labels else 22
    n = len(thumbs)
    cols = args.cols or max(1, math.ceil(math.sqrt(n * 16 / 9 * th / tw)))
    cols = min(cols, n)
    rows = math.ceil(n / cols)
    g = args.gap
    W = cols * tw + (cols + 1) * g
    H = rows * (th + label_h) + (rows + 1) * g

    sheet = OIIO.ImageBuf(OIIO.ImageSpec(W, H, 3, "float"))
    OIIO.ImageBufAlgo.fill(sheet, (0.08, 0.08, 0.08))
    for i, (t, label) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = g + c * (tw + g)
        y = g + r * (th + label_h + g)
        OIIO.ImageBufAlgo.paste(sheet, x, y, 0, 0, t)
        if label_h:
            # render_text needs a font; silently skip if none is available
            OIIO.ImageBufAlgo.render_text(sheet, x + 2, y + th + 16, label[:48], 13,
                                          textcolor=(0.85, 0.85, 0.85))

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    sheet = OIIO.ImageBufAlgo.clamp(sheet, 0.0, 1.0)
    if outp.suffix.lower() in (".jpg", ".jpeg", ".png"):
        sheet.set_write_format("uint8")
    if not sheet.write(str(outp)):
        die(sheet.geterror())
    console.print(f"[green]wrote[/] {outp} ({n} images, {cols}x{rows})")


if __name__ == "__main__":
    main()
