"""vidprep - ffmpeg recipes for video you already have.

    vidprep clip.mov -p h264                         review copy
    vidprep clip.mov -p hap --frame uhd              HAP at 3840x2160 for TouchDesigner/Resolume
    vidprep clip.mov -p h264 --frame 9x16            vertical social cut (centre crop)
    vidprep clip.mov -p gif --width 640 --trim 2:5   GIF of seconds 2-5
    vidprep clip.mov --frames out/clip.%04d.png      explode to frames
    vidprep "clip.%04d.png" --fps 25 -p prores-hq    frames back to a movie
    vidprep clip.mov --info                          what is this file?
    vidprep --list
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .common import console, die, need, out
from .presets import FRAMES, PRESETS, list_presets, reframe_filter


def probe(path: str) -> dict:
    ffprobe = need("ffprobe")
    res = subprocess.run([ffprobe, "-v", "error", "-print_format", "json", "-show_format",
                          "-show_streams", path], capture_output=True, text=True)
    if res.returncode:
        die(res.stderr.strip())
    return json.loads(res.stdout)


def show_info(path: str):
    info = probe(path)
    fmt = info["format"]
    out.print(f"[bold]{Path(path).name}[/]  {fmt.get('format_long_name', '')}  "
              f"{float(fmt.get('duration', 0)):.2f}s  {int(fmt.get('bit_rate', 0)) // 1000} kb/s")
    for s in info["streams"]:
        if s["codec_type"] == "video":
            rate = s.get("avg_frame_rate", "0/1")
            n, d = (int(x) for x in rate.split("/"))
            out.print(f"  video  {s.get('codec_name')} {s.get('profile', '')}  "
                      f"{s['width']}x{s['height']}  {n / d if d else 0:.3f} fps  "
                      f"{s.get('pix_fmt')}  {s.get('color_transfer', '')} {s.get('color_primaries', '')}")
        elif s["codec_type"] == "audio":
            out.print(f"  audio  {s.get('codec_name')}  {s.get('sample_rate')} Hz  "
                      f"{s.get('channels')} ch")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vidprep", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", help="movie, or printf frame pattern")
    ap.add_argument("-o", "--out")
    ap.add_argument("-p", "--preset", choices=PRESETS)
    ap.add_argument("--frame", choices=FRAMES, help="reframe (scale + centre crop)")
    ap.add_argument("--width", type=int, help="scale to width (keeps aspect)")
    ap.add_argument("--fps", type=float, help="input fps for frame patterns / output fps")
    ap.add_argument("--trim", help="start:end in seconds, e.g. 2:5")
    ap.add_argument("--start", type=int, default=None, help="first frame number for patterns")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--frames", metavar="PATTERN", help="explode movie to frames, e.g. out/f.%%04d.png")
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the ffmpeg command only")
    args = ap.parse_args(argv)

    if args.list:
        print(list_presets())
        return
    if not args.src:
        ap.error("src required")
    if args.info:
        show_info(args.src)
        return

    ffmpeg = need("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-stats", "-y"]
    is_pattern = "%" in args.src
    if is_pattern:
        cmd += ["-framerate", str(args.fps or 24)]
        if args.start is not None:
            cmd += ["-start_number", str(args.start)]
    if args.trim:
        a, b = args.trim.split(":")
        cmd += ["-ss", a, "-to", b]
    cmd += ["-i", args.src]

    filters = []
    if args.frame:
        filters.append(reframe_filter(args.frame))
    elif args.width:
        filters.append(f"scale={args.width}:-2:flags=lanczos")
    if args.fps and not is_pattern:
        filters.append(f"fps={args.fps}")

    if args.frames:
        Path(args.frames).parent.mkdir(parents=True, exist_ok=True)
        if filters:
            cmd += ["-vf", ",".join(filters)]
        cmd += ["-start_number", str(args.start if args.start is not None else 1001), args.frames]
    else:
        if not args.preset:
            ap.error("choose a preset with -p (see --list), or --frames / --info")
        ext, codec_args, _ = PRESETS[args.preset]
        codec_args = list(codec_args)
        if filters:
            if "-filter_complex" in codec_args:
                i = codec_args.index("-filter_complex")
                codec_args[i + 1] = codec_args[i + 1].replace("[0:v]", "[0:v]" + ",".join(filters) + ",", 1)
            else:
                cmd += ["-vf", ",".join(filters)]
        cmd += codec_args
        if args.no_audio or args.preset.startswith(("hap", "gif")) or is_pattern:
            cmd += ["-an"]
        else:
            if ext == ".mp4":
                cmd += ["-c:a", "aac", "-b:a", "192k"]
            elif ext == ".webm":
                cmd += ["-c:a", "libopus"]
            elif ext == ".mov":
                cmd += ["-c:a", "pcm_s16le"]
        src = Path(args.src.replace("%", "").replace("04d", ""))
        suffix = f"_{args.frame}" if args.frame else ""
        default = src.with_name(f"{src.stem.rstrip('._')}{suffix}_{args.preset}{ext}")
        cmd.append(args.out or str(default))

    if args.dry_run:
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        return
    console.print(f"[dim]{' '.join(cmd[1:])}[/]")
    rc = subprocess.call(cmd)
    if rc:
        die(f"ffmpeg failed ({rc})")
    console.print("[green]done[/]")


if __name__ == "__main__":
    main()
