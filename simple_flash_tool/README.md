# Simple Flash Tool (in development)

Vendor-neutral, J-Flash Lite-style GUI programmer.

## Goals

- **Any MCU** — driven by a local board database (board name → part number,
  flash base, sizes). Not tied to STM32: J-Link supports parts from ST, NXP,
  Nordic, TI, Renesas, and many others.
- **Both probes, auto-detected** — one scan finds ST-LINK (STM32CubeProgrammer
  CLI) and J-Link (J-Link Commander). Single probe → auto-selected; multiple →
  pick from a dropdown.
- **App-created local database** — SQLite at `~/.stm32flasher/boards.db`,
  auto-created and seeded on first launch from `boards.json` (this file also
  serves as the import/export format). Add / Edit / Delete boards from the UI.
- **Cross-platform** — Windows / Linux / macOS (both backend CLIs exist on all
  three).

> Note: J-Link programs any vendor's MCU. The ST-LINK backend works only for
> STM32 parts — its CLI supports nothing else. With no J-Link present, the
> tool is STM32-only by nature of the probe, not by design of the tool.

## Planned structure

```
simple_flash_tool/
├── simple_flash_tool.py    ← GUI (reuses proven framework patterns:
│                              bootstrap, single-instance guard, worker/queue)
├── board_db.py             ← SQLite: auto-create, seed from boards.json, CRUD
├── backends/
│   ├── stlink.py           ← STM32CubeProgrammer CLI backend
│   └── jlink.py            ← J-Link Commander backend (generated script files)
├── boards.json             ← seed data + import/export format
├── icon.png / icon.ico     ← own icon (TODO: to be designed)
├── build.sh / build.bat    ← own build scripts
└── (CI builds this alongside stm_flash_tool/)
```

## Status

- [x] Folder + seed database (`boards.json`)
- [ ] SQLite board database module (`board_db.py`)
- [ ] GUI (`simple_flash_tool.py`)
- [ ] J-Link backend (`backends/jlink.py`)
- [ ] ST-LINK backend (`backends/stlink.py`)
- [ ] Icon
- [ ] Build scripts + CI
