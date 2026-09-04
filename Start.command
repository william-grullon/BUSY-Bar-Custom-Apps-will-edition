#!/bin/bash
cd "$(dirname "$0")"

if command -v python3 &>/dev/null; then
    python3 launcher.py
else
    echo "Python 3 is not installed."
    echo "Please install Python 3.10 or newer."
    read -n 1 -s -r -p "Press any key to continue..."
fi
