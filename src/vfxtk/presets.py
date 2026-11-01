"""ffmpeg encode presets shared by exr2proxy and vidprep.

Each preset is (extension, ffmpeg output args, description). Edit freely -
this file is meant to grow with your own delivery specs.
"""

PRESETS: dict[str, tuple[str, list[str], str]] = {
    # --- review / editorial ---------------------------------------------
    "h264": (".mp4", ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                      "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
             "H.264 review copy, plays anywhere"),
    "h264-small": (".mp4", ["-c:v", "libx264", "-preset", "slow", "-crf", "26",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                   "H.264, small enough to message or email"),
    "h265": (".mp4", ["-c:v", "libx265", "-preset", "medium", "-crf", "22",
                      "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1"],
             "HEVC 10-bit, Apple-friendly tag"),
    "prores-proxy": (".mov", ["-c:v", "prores_ks", "-profile:v", "0", "-pix_fmt", "yuv422p10le",
                              "-vendor", "apl0"], "ProRes 422 Proxy"),
    "prores": (".mov", ["-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le",
                        "-vendor", "apl0"], "ProRes 422"),
    "prores-hq": (".mov", ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le",
                           "-vendor", "apl0"], "ProRes 422 HQ, editorial / Resolve"),
    "prores-4444": (".mov", ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le",
                             "-vendor", "apl0"], "ProRes 4444 with alpha"),
    "dnxhr-hq": (".mov", ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq", "-pix_fmt", "yuv422p"],
                 "DNxHR HQ for Avid/Windows pipelines"),
    # --- realtime / projection (TouchDesigner, Resolume, media servers) ---
    "hap": (".mov", ["-c:v", "hap", "-format", "hap"], "HAP, GPU-decoded playback"),
    "hap-alpha": (".mov", ["-c:v", "hap", "-format", "hap_alpha"], "HAP with alpha"),
    "hap-q": (".mov", ["-c:v", "hap", "-format", "hap_q"], "HAP Q, higher quality, bigger files"),
    # --- stills / web ------------------------------------------------------
    "gif": (".gif", ["-filter_complex",
                     "[0:v]fps=15,split[a][b];[a]palettegen=stats_mode=diff[p];"
                     "[b][p]paletteuse=dither=sierra2_4a"], "Looping GIF"),
    "webm": (".webm", ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-pix_fmt", "yuv420p"],
             "VP9 WebM for the web"),
}

# Social/aspect reframes, applied as a scale+crop (centre) before encoding.
FRAMES: dict[str, tuple[int, int]] = {
    "9x16": (1080, 1920),
    "1x1": (1080, 1080),
    "4x5": (1080, 1350),
    "16x9": (1920, 1080),
    "uhd": (3840, 2160),
    "dci4k": (4096, 2160),
}


def reframe_filter(name: str) -> str:
    w, h = FRAMES[name]
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={w}:{h},setsar=1")


def list_presets() -> str:
    lines = [f"  {k:<14} {v[2]}" for k, v in PRESETS.items()]
    lines.append("\n  frames (--frame): " + ", ".join(FRAMES))
    return "\n".join(lines)
