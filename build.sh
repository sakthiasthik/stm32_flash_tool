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

# Generate icon if not present
if [ ! -f "icon.png" ]; then
    echo "Run icon_gen.py first to generate icons."
    exit 1
fi

echo "Building..."
pyinstaller \
    --onefile \
    --windowed \
    --name "STM32-Flasher" \
    --add-data "icon.png:." \
    --collect-submodules tkinter \
    --clean \
    stm32_flasher.py

echo ""
echo "Done: dist/STM32-Flasher"
ls -lh dist/STM32-Flasher
