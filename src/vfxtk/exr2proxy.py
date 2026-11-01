"""exr2proxy - colour-managed movie from an image sequence.

Frames go through an OCIO display/view (ACES 2.0 SDR by default) and are
piped straight into ffmpeg, so there are no temp files.

    exr2proxy shot.####.exr                         H.264 next to the frames
    exr2proxy shot.####.exr -p prores-hq --fps 25
    exr2proxy shot.####.exr --width 1920 --burnin   frame numbers burnt in
    exr2proxy shot.####.exr --layer diffuse         preview an AOV
    exr2proxy shot.####.exr --view "Un-tone-mapped"
    exr2proxy --list                                show presets
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .common import console, die, guess_colorspace, load_rgb, need, oiio, resize_to, to_display
from .presets import PRESETS, list_presets
from .seq import parse_frames, resolve


def main(argv=None):
    ap = argparse.ArgumentParser(prog="exr2proxy", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="sequence pattern, frame, or folder")
    ap.add_argument("-o", "--out", help="output movie (default: next to the frames)")
    ap.add_argument("-p", "--preset", default="h264", choices=PRESETS)
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--width", type=int, help="output width (keeps aspect)")
    ap.add_argument("--frames", help="subset, e.g. 1001-1050 or 1001-1100x2")
    ap.add_argument("--layer", help="EXR layer/AOV to use instead of RGB")
    ap.add_argument("--from", dest="src", help="input colour space (default: guessed)")
    ap.add_argument("--display", help="OCIO display (default from config)")
    ap.add_argument("--view", help="OCIO view (default from config)")
    ap.add_argument("--burnin", action="store_true", help="burn in frame numbers")
    ap.add_argument("--list", action="store_true", help="list presets and exit")
    args = ap.parse_args(argv)

    if args.list:
        print(list_presets())
        return
    if not args.target:
        ap.error("target required")
    ffmpeg = need("ffmpeg")
    OIIO = oiio()

    seqs = [s for s in resolve(args.target) if s.padding]
    if not seqs:
        die("no image sequence found")
    if len(seqs) > 1:
        names = "\n  ".join(s.name for s in seqs)
        die(f"several sequences match - pick one:\n  {names}")
    seq = seqs[0]
    frames = seq.frames
    if args.frames:
        wanted = set(parse_frames(args.frames))
        frames = [f for f in frames if f in wanted]
    if seq.missing:
        console.print(f"[yellow]warning:[/] {len(seq.missing)} missing frame(s) - "
                      "holding previous frame")

    ext, codec_args, _ = PRESETS[args.preset]
    outp = Path(args.out) if args.out else seq.directory / f"{seq.head.rstrip('._-')}{ext}"
    if args.layer and not args.out:
        outp = outp.with_name(f"{outp.stem}_{args.layer}{ext}")

    # probe the first frame for size
    rgb, spec = load_rgb(str(seq.path(frames[0])), args.layer)
    rgb = resize_to(rgb, width=args.width) if args.width else resize_to(
        rgb, width=spec.full_width)
    w, h = rgb.spec().width, rgb.spec().height
    space = args.src or guess_colorspace(str(seq.path(frames[0])), spec)
    console.print(f"[dim]{seq.name}: {len(frames)} frames, {w}x{h}, {space} -> "
                  f"{args.display or 'default display'} / {args.view or 'default view'}[/]")

    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-framerate", str(args.fps), "-i", "-"]
    if args.burnin:
        vf = (f"drawtext=text='%{{eif\\:n+{frames[0]}\\:d}}':x=w-tw-20:y=h-th-20:"
              "fontsize=h/30:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=6")
        if "-filter_complex" in codec_args:
            console.print("[yellow]burn-in ignored for this preset[/]")
        else:
            cmd += ["-vf", vf]
    cmd += codec_args + [str(outp)]

    outp.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    have = set(seq.frames)
    last_path = None
    try:
        with console.status("encoding") as st:
            for i, f in enumerate(range(frames[0], frames[-1] + 1)):
                if args.frames and f not in frames:
                    continue
                path = seq.path(f) if f in have else last_path
                last_path = path
                st.update(f"frame {f} ({i + 1}/{frames[-1] - frames[0] + 1})")
                buf, _ = load_rgb(str(path), args.layer)
                buf = resize_to(buf, w, h)
                buf = to_display(buf, space, args.display, args.view)
                buf = OIIO.ImageBufAlgo.clamp(buf, 0.0, 1.0)
                px = buf.get_pixels(OIIO.UINT8)
                proc.stdin.write(px.tobytes())
    except BrokenPipeError:
        pass
    finally:
        if proc.stdin:
            proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        die(f"ffmpeg failed ({rc})")
    console.print(f"[green]wrote[/] {outp}")


if __name__ == "__main__":
    main()
