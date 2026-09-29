#!/usr/bin/env bash
# Install ~/.local/bin/text2img-qwen and img2img-qwen pointing at the Qwen venv.
# Intentionally NOT named text2img/img2img by default — on NixOS workstations those
# names often belong to system llada-cli (LLaDA-Image Turbo).
# Set INSTALL_AS_TEXT2IMG=1 to also install text2img/img2img names (and keep -qwen symlinks).
set -euo pipefail

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV_DIR="${AI_MEDIA_QWEN_VENV:-$XDG_DATA_HOME/ai-media/envs/qwen}"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

# Capture gcc/zlib/etc. from AI_MEDIA_EXTRA_LD_PATH at install time (NixOS).
EXTRA_LD="${AI_MEDIA_EXTRA_LD_PATH:-}"

write_wrapper() {
  local NAME="$1"
  local INNER="$2"
  local WRAPPER="$BIN_DIR/$NAME"
  local VENV_EXE="${VENV_DIR}/bin/${INNER}"
  if [[ ! -x "$VENV_EXE" ]]; then
    echo "missing venv entrypoint: $VENV_EXE" >&2
    echo "Run scripts/setup_qwen_env.sh first." >&2
    exit 1
  fi
  cat > "$WRAPPER" <<WRAP
#!/usr/bin/env bash
# Qwen-Image-2.1 ${INNER} (ai-media-cli)
export LD_LIBRARY_PATH="/run/opengl-driver/lib${EXTRA_LD:+:$EXTRA_LD}\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export TRITON_LIBCUDA_PATH="/run/opengl-driver/lib"
exec "${VENV_EXE}" "\$@"
WRAP
  chmod +x "$WRAPPER"
  echo "Installed $WRAPPER → $VENV_EXE"
}

for pair in "text2img-qwen:text2img" "img2img-qwen:img2img"; do
  NAME="${pair%%:*}"
  INNER="${pair##*:}"
  # Migrate legacy shadowing wrappers if present and we are not installing as text2img
  if [[ "${INSTALL_AS_TEXT2IMG:-0}" != "1" ]]; then
    LEGACY="$BIN_DIR/$INNER"
    if [[ -f "$LEGACY" ]] && grep -q 'envs/qwen' "$LEGACY" 2>/dev/null; then
      mv "$LEGACY" "${LEGACY}.bak.qwen.$(date +%Y%m%d%H%M%S)"
      echo "Moved legacy $LEGACY aside (was shadowing system llada-cli)"
    fi
  fi
  write_wrapper "$NAME" "$INNER"
done

if [[ "${INSTALL_AS_TEXT2IMG:-0}" == "1" ]]; then
  write_wrapper "text2img" "text2img"
  write_wrapper "img2img" "img2img"
  ln -sfn text2img "${BIN_DIR}/text2img-qwen"
  ln -sfn img2img "${BIN_DIR}/img2img-qwen"
  echo "Also installed text2img/img2img (INSTALL_AS_TEXT2IMG=1); -qwen names are symlinks"
fi

# Umbrella CLI
UMBRELLA="$BIN_DIR/ai-media"
cat > "$UMBRELLA" <<WRAP
#!/usr/bin/env bash
set -euo pipefail
VENV="${VENV_DIR}"
BIN="\$VENV/bin/ai-media"
[[ -x "\$BIN" ]] || { echo "ai-media: missing \$BIN — run scripts/setup_qwen_env.sh" >&2; exit 127; }
export LD_LIBRARY_PATH="/run/opengl-driver/lib${EXTRA_LD:+:$EXTRA_LD}\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export TRITON_LIBCUDA_PATH="/run/opengl-driver/lib"
exec "\$BIN" "\$@"
WRAP
chmod +x "$UMBRELLA"
echo "Installed $UMBRELLA → $VENV_DIR/bin/ai-media"
echo "Verify: command -v text2img-qwen ai-media; text2img-qwen --version; ai-media --version"
