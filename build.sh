#!/bin/bash
# Build standalone Linux executable
# Requires: pip install pyinstaller

set -e

echo "=== STM32 Flash Tool — Linux Build ==="

# Check PyInstaller
if ! command -v pyinstaller &>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

echo "Building..."
pyinstaller \
    --onefile \
    --windowed \
    --name "STM32-Flasher" \
    --clean \
    stm32_flasher.py

echo ""
echo "Done: dist/STM32-Flasher"
ls -lh dist/STM32-Flasher
