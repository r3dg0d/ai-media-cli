#!/usr/bin/env bash
# Install ~/.local/bin/editvideo pointing at the scail venv (NOT qwen).
set -euo pipefail

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV_DIR="${AI_MEDIA_SCAIL_VENV:-$XDG_DATA_HOME/ai-media/envs/scail}"
BIN_DIR="${HOME}/.local/bin"
WRAPPER="$BIN_DIR/editvideo"
SCAIL_REPO="${AI_MEDIA_SCAIL_REPO:-$HOME/Projects/SCAIL-2}"

mkdir -p "$BIN_DIR"

# Preserve old wrapper if it exists and doesn't already mention scail
if [[ -f "$WRAPPER" ]] && ! grep -q 'envs/scail' "$WRAPPER" 2>/dev/null; then
  cp -a "$WRAPPER" "${WRAPPER}.bak.qwen.$(date +%Y%m%d%H%M%S)" || true
fi

cat > "$WRAPPER" <<WRAP
#!/usr/bin/env bash
# ai-media editvideo → SCAIL-2 env (not qwen)
set -euo pipefail
VENV="${VENV_DIR}"
export AI_MEDIA_SCAIL_VENV="\$VENV"
export AI_MEDIA_SCAIL_REPO="\${AI_MEDIA_SCAIL_REPO:-${SCAIL_REPO}}"
# NixOS NVIDIA + typical CUDA libs
export LD_LIBRARY_PATH="/run/opengl-driver/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
if [[ -d "\$AI_MEDIA_SCAIL_REPO" ]]; then
  export PYTHONPATH="\$AI_MEDIA_SCAIL_REPO\${PYTHONPATH:+:\$PYTHONPATH}"
fi
exec "\$VENV/bin/editvideo" "\$@"
WRAP
chmod +x "$WRAPPER"
echo "Installed $WRAPPER → $VENV_DIR/bin/editvideo"
echo "Verify: head -n 5 $WRAPPER && editvideo --version"
