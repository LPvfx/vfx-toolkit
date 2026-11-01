# vfx-toolkit

Personal VFX/CG/video toolkit for a Mac (Apple Silicon). Free software only.
The owner is a senior VFX supervisor: assume fluency with EXR, AOVs, OCIO/ACES,
USD, sequences and editorial formats. Don't explain the domain; be precise.

## Structure
- `src/vfxtk/` - one module per CLI command, each with `main(argv=None)`.
  Shared code: `seq.py` (sequence parsing), `common.py` (OCIO, image IO,
  display transforms), `presets.py` (ffmpeg presets/reframes).
- Commands are registered in `[project.scripts]` in `pyproject.toml`.
- `Brewfile` + `bootstrap.sh` install apps and the tools (`uv tool install --editable .`).

## Conventions
- Never overwrite source media. Tools that write require `-o` or write
  alongside with a new name.
- Everything colour-related goes through OCIO; default config is
  `ocio://default` unless `$OCIO` is set. Don't hardcode gamma maths.
- Sequences: support `####`, `%04d`, a single frame, or a folder via `seq.resolve()`.
- Use OpenImageIO for image IO, ffmpeg (via subprocess) for movies, pxr for USD.
- Output via `rich`; `--json` where a tool reports data.
- Keep tools dependency-light; argparse, not click/typer.

## Testing
`uv run --extra dev pytest` - tests generate their own fixtures (multi-layer
EXRs with a gap, PNGs, a USD with a missing reference). Add a test for every
new tool or flag. Run `vfxtk doctor` to check the environment.
