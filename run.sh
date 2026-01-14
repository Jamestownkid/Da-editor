#!/bin/bash
# Da Editor - Linux/Mac Run Script
# =================================
# one-click launcher for the app
# 
# usage: ./run.sh

echo "========================================="
echo "  DA EDITOR - B-Roll Automation"
echo "========================================="
echo ""

# find the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# check if we should run electron or python
if [ -d "electron" ] && [ -f "electron/package.json" ]; then
    # check if node_modules exists
    if [ ! -d "electron/node_modules" ]; then
        echo "First run detected - setting up..."
        python3 setup.py
    fi
    
    echo "Starting Electron app..."
    cd electron
    npm run dev
else
    echo "Starting Python app..."
    python3 main.py
fi
