#!/bin/bash
# DA EDITOR - UPDATE AND OPEN
# ===========================
# run this to get latest updates and open the app

cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "   DA EDITOR - UPDATING..."
echo "========================================"
echo ""

echo "[+] Pulling latest from GitHub..."
git pull origin main 2>/dev/null || true

echo "[+] Updating Python dependencies..."
pip install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt --quiet 2>/dev/null || true

echo "[+] Updating Electron dependencies..."
cd electron && npm install --silent 2>/dev/null || true
cd ..

echo ""
echo "[+] Update complete! Starting app..."
echo ""

./open.sh

