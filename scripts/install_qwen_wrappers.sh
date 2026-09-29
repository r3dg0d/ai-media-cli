#!/usr/bin/env bash
# Install ~/.local/bin/text2img-qwen and img2img-qwen pointing at the Qwen venv.
# Intentionally NOT named text2img/img2img — on NixOS workstations those names
# belong to system llada-cli (LLaDA-Image Turbo).
set -euo pipefail

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV_DIR="${AI_MEDIA_QWEN_VENV:-$XDG_DATA_HOME/ai-media/envs/qwen}"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

# Capture gcc/zlib/etc. from AI_MEDIA_EXTRA_LD_PATH at install time (NixOS).
EXTRA_LD="${AI_MEDIA_EXTRA_LD_PATH:-}"

for pair in "text2img-qwen:text2img" "img2img-qwen:img2img"; do
  NAME="${pair%%:*}"
  INNER="${pair##*:}"
  WRAPPER="$BIN_DIR/$NAME"
  # Migrate legacy shadowing wrappers if present
  LEGACY="$BIN_DIR/$INNER"
  if [[ -f "$LEGACY" ]] && grep -q 'envs/qwen' "$LEGACY" 2>/dev/null; then
    mv "$LEGACY" "${LEGACY}.bak.qwen.$(date +%Y%m%d%H%M%S)"
    echo "Moved legacy $LEGACY aside (was shadowing system llada-cli)"
  fi
  cat > "$WRAPPER" <<WRAP
#!/usr/bin/env bash
# Qwen-Image-2.1 ${INNER} (ai-media). System \`${INNER}\` is LLaDA (llada-cli).
export LD_LIBRARY_PATH="/run/opengl-driver/lib${EXTRA_LD:+:$EXTRA_LD}\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export TRITON_LIBCUDA_PATH="/run/opengl-driver/lib"
exec "${VENV_DIR}/bin/${INNER}" "\$@"
WRAP
  chmod +x "$WRAPPER"
  echo "Installed $WRAPPER → $VENV_DIR/bin/$INNER"
done

# Optional umbrella
UMBRELLA="$BIN_DIR/ai-media"
cat > "$UMBRELLA" <<WRAP
#!/usr/bin/env bash
set -euo pipefail
VENV="${VENV_DIR}"
BIN="\$VENV/bin/ai-media"
[[ -x "\$BIN" ]] || { echo "ai-media: missing \$BIN" >&2; exit 127; }
export LD_LIBRARY_PATH="/run/opengl-driver/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export TRITON_LIBCUDA_PATH="/run/opengl-driver/lib"
exec "\$BIN" "\$@"
WRAP
chmod +x "$UMBRELLA"
echo "Installed $UMBRELLA → $VENV_DIR/bin/ai-media"
echo "Verify: command -v text2img text2img-qwen; text2img --help | head -1; text2img-qwen --help | head -1"
