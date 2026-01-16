#!/bin/bash
# DA EDITOR - ADD TO SYSTEM APPS
# ===============================
# run this to add Da Editor to your applications menu
# works on Linux (Ubuntu, Pop!_OS, Debian, etc)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$SCRIPT_DIR/da-editor.desktop"

echo ""
echo "========================================"
echo "   DA EDITOR - ADDING TO APPS..."
echo "========================================"
echo ""

# update the desktop file with the correct path
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Da Editor
Comment=B-roll Video Automation Tool
Exec=/bin/bash -c "cd $SCRIPT_DIR && ./open.sh"
Icon=$SCRIPT_DIR/assets/icons/app_icon.png
Terminal=false
Categories=AudioVideo;Video;
Keywords=video;editor;broll;automation;
StartupNotify=true
EOF

# copy to user's applications directory
mkdir -p ~/.local/share/applications
cp "$DESKTOP_FILE" ~/.local/share/applications/da-editor.desktop

# make executable
chmod +x ~/.local/share/applications/da-editor.desktop

# update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database ~/.local/share/applications 2>/dev/null || true
fi

echo ""
echo "[+] Done! Da Editor has been added to your applications."
echo "[+] Look for 'Da Editor' in your app launcher."
echo ""

