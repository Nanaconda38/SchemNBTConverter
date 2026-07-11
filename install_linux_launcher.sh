#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
WRAPPER="$BIN_DIR/schem-nbt-converter"
DESKTOP_FILE="$APP_DIR/schem-nbt-converter.desktop"

mkdir -p "$BIN_DIR" "$APP_DIR"
cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
cd -- "$PROJECT_DIR"
exec "$PROJECT_DIR/run_linux.sh"
EOF
chmod +x "$WRAPPER"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Schem & Litematic to NBT
Comment=Convert Minecraft schematics to vanilla NBT structures
Exec=$WRAPPER
Icon=application-x-executable
Terminal=false
Categories=Utility;Game;
EOF
chmod +x "$DESKTOP_FILE"

echo "Launcher installed: $DESKTOP_FILE"
echo "It should now appear in your application menu."
