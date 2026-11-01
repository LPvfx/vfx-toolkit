# vfx-toolkit

Free, day-one VFX / CG / video setup for a Mac, plus a set of small,
colour-managed command-line tools built on OpenImageIO, OpenColorIO, USD and
ffmpeg.

```bash
git clone https://github.com/LPvfx/vfx-toolkit && cd vfx-toolkit
./bootstrap.sh          # Homebrew apps + tools, then `vfxtk doctor`
./bootstrap.sh --tools  # just the CLI tools
```

## What gets installed

**Apps (all free):** Blender, DaVinci Resolve, TouchDesigner (non-commercial),
OBS, DJV (EXR / sequence viewer), VLC.

**Command line:** ffmpeg, OpenImageIO (`oiiotool`, `iinfo`, `maketx`),
OpenColorIO, exiftool, ImageMagick, uv.

**Python (in an isolated uv tool env):** OpenImageIO, OpenColorIO, OpenEXR,
usd-core, numpy, rich.

## The tools

| command | what it does |
|---|---|
| `seqinfo` | Every sequence in a folder: frame range, missing frames, resolution, channels, bit depth, compression, size. `--check` reads every frame to find corrupt ones. `--json` for scripts. |
| `layers` | Lists AOVs in a multi-layer / multi-part EXR; `-e diffuse` or `--split` extracts them to their own sequences. |
| `contact` | Contact sheet of a folder, or N frames across a sequence, colour-managed, with labels. |
| `exr2proxy` | EXR sequence → H.264 / ProRes / HAP movie through an OCIO display/view, frames piped straight into ffmpeg. Holds missing frames, optional frame-number burn-in, can preview any AOV. |
| `ocio-convert` | Batch colour space / display conversion and format change; `--tx` writes mipmapped textures; `--spaces` lists the config. |
| `usdinfo` | USD health check: prim/mesh/face counts, materials and unbound meshes, variants, up-axis and units, every dependency and anything unresolved. `--tree 3` prints the hierarchy. |
| `vidprep` | ffmpeg recipes for footage you already have: HAP for TouchDesigner/Resolume, ProRes/DNxHR, `--frame 9x16` social reframes, GIFs, explode to frames and back. `--info` describes a file, `--dry-run` shows the command. |

Run `vfxtk` for the list, or any tool with `-h` for examples.

```bash
seqinfo ~/renders                                    # what's here, what's missing
layers beauty.1001.exr                               # which AOVs?
exr2proxy beauty.####.exr -p prores-hq --fps 25 --burnin
contact beauty.####.exr -n 24 -o review.jpg
ocio-convert textures/ --from "sRGB Encoded Rec.709 (sRGB)" --to ACEScg --tx -o tex_acescg/
usdinfo asset.usd --deps
vidprep loop.mov -p hap --frame uhd                  # ready for projection
```

## Colour

Everything goes through OpenColorIO. With no `$OCIO` set the tools use OCIO's
built-in ACES CG config (`ocio://default`, ACES 2.0 view transforms), so there
is nothing to download. Point `$OCIO` at a show config and every tool follows it.

Input colour space is guessed (float EXR → ACEScg, everything else → sRGB);
override with `--from` on any tool. `ocio-convert --spaces` lists every
space, display and view available.

## Layout

```
Brewfile                apps and CLI tools
bootstrap.sh            one-shot setup
src/vfxtk/seq.py        sequence detection (####, %04d, folders, single frames)
src/vfxtk/common.py     OCIO, image loading, display transforms
src/vfxtk/presets.py    ffmpeg presets and reframes - add your own here
src/vfxtk/<tool>.py     one file per command
tests/                  end-to-end tests with generated fixtures
```

Installed editable, so changes in `src/` take effect immediately. Add a new
tool by dropping a module with a `main()` in `src/vfxtk/` and adding it to
`[project.scripts]` in `pyproject.toml`, then rerun `./bootstrap.sh --tools`.

## Tests

```bash
uv run --extra dev pytest
```
