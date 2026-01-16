#!/bin/bash
# DA EDITOR - OPEN APP
# ====================
# just run this to open the app
# kills any existing instances first

cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "   DA EDITOR - STARTING..."
echo "========================================"
echo ""

# KILL ANY EXISTING PROCESSES FIRST (fixes port 5173 already in use)
echo "[+] Cleaning up old processes..."
pkill -f "vite --port 5173" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null
pkill -f "electron.*da-editor" 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
sleep 1

# check if electron is set up
if [ -d "electron/node_modules" ]; then
    echo "[+] Starting Electron app..."
    cd electron
    
    # compile typescript
    npx tsc -p tsconfig.electron.json 2>/dev/null
    
    # start vite in background with auto-kill on exit
    npx vite --port 5173 &
    VITE_PID=$!
    
    # wait for vite to start
    echo "[+] Waiting for Vite server..."
    sleep 3
    
    # check if vite actually started
    if ! kill -0 $VITE_PID 2>/dev/null; then
        echo "[!] Vite failed to start. Retrying..."
        lsof -ti:5173 | xargs kill -9 2>/dev/null
        sleep 1
        npx vite --port 5173 &
        VITE_PID=$!
        sleep 3
    fi
    
    # start electron
    npx electron . &
    ELECTRON_PID=$!
    
    echo "[+] App is running!"
    echo "[+] Press Ctrl+C or close the window to exit."
    
    # trap ctrl+c to cleanup
    trap "echo 'Shutting down...'; kill $VITE_PID $ELECTRON_PID 2>/dev/null; exit 0" SIGINT SIGTERM
    
    # wait for electron to exit
    wait $ELECTRON_PID 2>/dev/null
    
    # cleanup vite when electron closes
    kill $VITE_PID 2>/dev/null
    echo "[+] Done!"
else
    echo "[!] Electron not set up. Running Python GUI instead..."
    python3 main.py
fi
