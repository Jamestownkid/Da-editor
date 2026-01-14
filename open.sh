#!/bin/bash
# DA EDITOR - OPEN APP
# ====================
# just run this to open the app

cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "   DA EDITOR - STARTING..."
echo "========================================"
echo ""

# check if electron is set up
if [ -d "electron/node_modules" ]; then
    echo "[+] Starting Electron app..."
    cd electron
    
    # compile typescript
    npx tsc -p tsconfig.electron.json 2>/dev/null
    
    # start vite in background
    npx vite --port 5173 &
    VITE_PID=$!
    
    # wait for vite to start
    sleep 2
    
    # start electron
    npx electron . &
    ELECTRON_PID=$!
    
    echo "[+] App is running!"
    echo "[+] Close this terminal window when done."
    
    # wait for electron to exit
    wait $ELECTRON_PID 2>/dev/null
    
    # cleanup
    kill $VITE_PID 2>/dev/null
else
    echo "[!] Electron not set up. Running Python GUI instead..."
    python3 main.py
fi

