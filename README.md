# STM32 Flash Tool

Lightweight, cross-platform GUI tool for flashing STM32 microcontrollers in mass production.

**Single file. Zero dependencies. Double-click to run.**

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.7%2B-green)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

## Features

- ⚡ **Flash + Verify** — one click writes firmware, verifies it, and starts execution
- 🔍 **Verify Only** — re-check an already-flashed chip without re-writing
- 🧵 **Non-blocking** — all operations run in background threads, UI never freezes
- 🔌 **Auto-detection** — finds ST-LINK probes and STM32CubeProgrammer CLI automatically
- 🪟🐧 **Cross-platform** — Windows and Linux
- 📦 **Self-bootstrapping** — auto-installs missing system packages on Linux
- 💾 **Remembers settings** — CLI path, flash address, last directory

## Screenshot

```
┌──────────────────────────────────────┐
│  STM32 Flash Tool                    │
│                                      │
│  CLI:  STM32_Programmer_CLI          │
│  Board: [▼ ST-LINK SN: XXXX] [Refresh]│
│  File:  [_______________] [Browse]   │
│  Addr:  [0x08000000] (BIN only)      │
│                                      │
│  ┌────────────────────────────────┐  │
│  │     FLASH + VERIFY             │  │
│  └────────────────────────────────┘  │
│  [Verify Only]                       │
│                                      │
│  ● PASS — flashed + verified OK      │
└──────────────────────────────────────┘
```

## Prerequisites

### Required (either way)
- **STM32CubeProgrammer CLI** — [Download from ST.com](https://www.st.com/en/development-tools/stm32cubeprog.html)

### To run the `.py` file directly
- **Python 3.7+** — [Download from python.org](https://python.org)
- tkinter ships with Python on Windows. On Linux, the app auto-installs it.

### To run the standalone `.exe` / binary
- Nothing. Just the file.

## Quick Start

### Option A: Run the Python file

```bash
python stm32_flasher.py
```

Double-click also works on most systems.

### Option B: Build a standalone executable

**Windows:**
```cmd
pip install pyinstaller
build.bat
```
Output: `dist\STM32-Flasher.exe` (~15 MB) — share this, no Python needed.

**Linux:**
```bash
pip install pyinstaller
bash build.sh
```
Output: `dist/STM32-Flasher` (~15 MB) — share this, no Python needed.

## How It Works

```
User clicks Flash + Verify
        │
        ▼
STM32_Programmer_CLI -c port=SWD sn=<SN> -w firmware.bin 0x08000000 -v -g
        │                              │         │            │  │
        │                              │         │            │  └── run after flash
        │                              │         │            └── verify
        │                              │         └── write firmware
        │                              └── connect to probe
        └── CLI executable
```

| Button | CLI Flags | Use Case |
|--------|-----------|----------|
| **Flash + Verify** | `-w file [addr] -v -g` | Production — write, verify, run |
| **Verify Only** | `-v file [addr]` | Spot-check without re-flashing |

## File Structure

```
stm32_flash_tool/
├── stm32_flasher.py      ← The app (~310 lines, stdlib only)
├── STM32flash_gui.py     ← Legacy version (reference)
├── build.bat             ← Build Windows .exe
├── build.sh              ← Build Linux binary
├── README.md
├── LICENSE
└── .gitignore
```

## Config

Settings are auto-saved to `~/.stm32flasher.json`:

```json
{
  "cli_path": "/opt/st/.../STM32_Programmer_CLI",
  "flash_address": "0x08000000",
  "last_dir": "/home/user/firmware"
}
```

No settings UI — it just works.

## License

MIT — see [LICENSE](LICENSE)
