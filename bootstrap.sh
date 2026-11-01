#!/usr/bin/env bash
# One-shot setup for a fresh Mac (also works on Linux, minus the Brewfile apps).
#
#   ./bootstrap.sh            apps + tools
#   ./bootstrap.sh --tools    just the CLI tools (skip Homebrew apps)
set -euo pipefail
cd "$(dirname "$0")"

say() { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }

if [[ "${1:-}" != "--tools" && "$(uname)" == "Darwin" ]]; then
  if ! command -v brew >/dev/null; then
    say "Installing Homebrew"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
  say "Installing apps and command-line tools (Brewfile)"
  brew bundle --file=Brewfile || echo "some Brewfile entries failed - see above, install those by hand"
fi

if ! command -v uv >/dev/null; then
  say "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

say "Installing vfxtk command-line tools (editable - edits to src/ apply instantly)"
uv tool install --force --editable . --python 3.12

say "Checking"
"$HOME/.local/bin/vfxtk" doctor || true

cat <<'EOF'

Done. Commands now on your PATH:
  seqinfo  layers  contact  exr2proxy  ocio-convert  usdinfo  vidprep
Run `vfxtk` for the list, or any tool with -h.
(If they aren't found, run: uv tool update-shell  and open a new terminal.)
EOF
