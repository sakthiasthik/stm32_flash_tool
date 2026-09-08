# STM32 Flash Tool — Bug Report & Roadmap

Report date: 2026-09-07 · Applies to: `v1.0.0` (`stm_flash_tool/stm32_flasher.py`)

**Fixed on `dev` branch (2026-09-08):**
- ✅ Bug #1 — single-instance guard (mutex on Windows, PID lockfile on Linux) — tested
- ✅ Bug #2 — flash timeout now works when the CLI hangs
- ✅ Bug #3 — address field stays disabled for ELF/HEX after operations
- ✅ Bug #6 — no more flashing black console window on Windows

---

## ⭐ BUG #1 — CRITICAL — App opens MULTIPLE windows on Windows

**Symptom (reported):** Clicking `STM32-Flasher.exe` opens the app several times.
Each click = one new window, and they pile up.

**Root cause:** The app has **no single-instance guard**.
`main()` (`stm_flash_tool/stm32_flasher.py:692-694`) always creates a new window and never checks
whether another copy is already running.

Why it feels "sudden":
1. The `.exe` is built with PyInstaller `--onefile`. Every launch first unpacks
   itself to a temp folder, which takes **1–3 seconds with no visible feedback**.
   Users click the icon again thinking the first click didn't work → 2, 3, 4 windows.
2. There is no mutex / lock file / process check to stop the second instance.
3. If STM32CubeProgrammer CLI is not installed, *each* window additionally pops a
   "CLI Not Found" warning dialog 0.5 s after launch (`stm_flash_tool/stm32_flasher.py:404-406`),
   making it look like even more popups.

**Side effects of multiple instances:**
- All instances write `~/.stm32flasher.json` at the same time (non-atomic write,
  `stm_flash_tool/stm32_flasher.py:244-247`) → config can get corrupted.
- Two instances can each grab the ST-LINK and race each other during flashing.

**Fix (Windows):** named mutex before creating the Tk window:

```python
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "STM32FlashTool_SingleInstance")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        messagebox.showwarning("Already Running", "STM32 Flash Tool is already open.")
        sys.exit(0)
```

(Cross-platform fallback: lock file in the user's temp dir holding the PID;
skip the exit if that PID is no longer alive.)

---

## Bug list — `stm_flash_tool/stm32_flasher.py`

| # | Severity | Bug | Location | Suggested fix |
|---|----------|-----|----------|---------------|
| 2 | **High** | **Flash timeout never fires if the CLI hangs.** `for line in proc.stdout` blocks until the process closes stdout (EOF). `proc.wait(timeout=120)` is only reached *after* EOF. A hung `STM32_Programmer_CLI` (USB glitch, stuck probe) leaves the UI "busy" forever. | `stm_flash_tool/stm32_flasher.py:564-566` | Read output in a helper thread and loop `proc.wait(timeout=...)`, or use `proc.communicate(timeout=120)`. |
| 3 | **High** | **Address field re-enabled for non-BIN files after every operation.** `_on_file_changed()` disables the address entry for ELF/HEX, but `_set_busy(False)` unconditionally sets it back to `normal`. After one flash/scan, the address box is editable for ELF too. | `stm_flash_tool/stm32_flasher.py:380-389` vs `460-468` | In `_set_busy(False)`, re-apply `_on_file_changed()` instead of forcing `normal`. |
| 4 | Medium | **`last_dir` is saved but never used.** File dialog always opens in the default directory; the saved setting is dead data. | `stm_flash_tool/stm32_flasher.py:241` vs `433-441` | Pass `initialdir=data["last_dir"]` to `askopenfilename`. |
| 5 | Medium | **No validation of the flash address.** Any text ("banana", empty string) is passed straight to the CLI → confusing CLI errors. | `stm_flash_tool/stm32_flasher.py:519, 535` | Validate `^0x[0-9A-Fa-f]{1,8}$` and show a clear error before launching. |
| 6 | Medium | **Windows: a black console window flashes on every flash operation.** The app is built `console=False`, but the CLI is a console program; spawning it without flags allocates a new console each time. | `stm_flash_tool/stm32_flasher.py:557-563` | Add `creationflags=subprocess.CREATE_NO_WINDOW` on Windows. |
| 7 | Medium | **Enter key anywhere triggers Flash.** `<Return>` is bound on the whole root window. An operator typing in the address field and pressing Enter to "confirm" accidentally starts a flash when all inputs happen to be valid. | `stm_flash_tool/stm32_flasher.py:333-334` | Bind Return to the Flash button only (or require focus on the button). |
| 8 | Medium | **Config writes are not atomic.** Kill/power-loss mid-write (or two instances writing) corrupts `~/.stm32flasher.json`, silently wiping saved settings. | `stm_flash_tool/stm32_flasher.py:244-247` | Write to `*.tmp` then `os.replace()`. |
| 9 | Low | **Bootstrap messages are invisible in the .exe.** `_bootstrap()` prints warnings (CLI not found, etc.) to stdout, but the frozen build has no console — output goes nowhere. | `stm_flash_tool/stm32_flasher.py:24-65` | Route to the GUI status bar, or keep console=False but show a startup dialog. |
| 10 | Low | **`refresh_boards()` has no re-entry guard.** It doesn't check `self._busy` before spawning a scan thread; a stale scan finishing later calls `_set_busy(False)` and re-enables controls. | `stm_flash_tool/stm32_flasher.py:393-431` | Early-return if `self._busy`. |
| 11 | Low | **Scan only understands ST-LINK.** Output regex matches `ST-LINK SN` only — J-Link or DFU-connected boards show as "No board found". | `stm_flash_tool/stm32_flasher.py:417` | Add J-Link detection (see Roadmap). |

---

## Bug list — legacy `stm_flash_tool/STM32flash_gui.py` (kept for reference)

| # | Bug | Location |
|---|-----|----------|
| L1 | SN regex `(\w+)` misses serial numbers containing `-` | `stm_flash_tool/STM32flash_gui.py:18` |
| L2 | `list(set(sns))` shuffles board order on every refresh | `stm_flash_tool/STM32flash_gui.py:21` |
| L3 | No timeout on `subprocess.run` → UI freezes forever on a hung CLI | `stm_flash_tool/STM32flash_gui.py:17, 82` |
| L4 | Flash runs on the main thread → whole window freezes during flashing | `stm_flash_tool/STM32flash_gui.py:82` |
| L5 | No Verify step (`-v` missing) and no address field for BIN | `stm_flash_tool/STM32flash_gui.py:73-79` |
| L6 | Same single-instance bug as #1 | whole file |

---

## Roadmap (decided architecture)

### 1. Separate tool: `simple_flash_tool/` (in development)
A vendor-neutral, J-Flash Lite-style tool in its own folder — the existing
STM32 Flash Tool stays untouched. The name is probe/vendor-neutral because
J-Link programs any MCU (ST, NXP, Nordic, TI, Renesas, ...). The ST-LINK
backend naturally supports only STM32 parts (its CLI supports nothing else).

### 2. J-Link + ST-LINK auto-detection
- One scan runs both CLIs: `STM32_Programmer_CLI -l` (ST-LINK) and
  `JLinkExe -ShowEmuList` (J-Link); combined probe list labeled by type.
- Single probe connected → auto-selected. Multiple → dropdown.
- Program via generated J-Link command files (J-Flash Lite style):
  ```
  device <part>
  si SWD
  speed 4000
  connect
  loadfile firmware.bin 0x08000000
  verifybin firmware.bin 0x08000000
  r
  g
  exit
  ```

### 3. Board database — app-created, local
- SQLite (`sqlite3`, stdlib) at `~/.stm32flasher/boards.db`, auto-created and
  seeded on first launch from `simple_flash_tool/boards.json` (which doubles
  as the import/export format).
- Board Name → part number, flash base, sizes, interface — any vendor.
  Add / Edit / Delete boards from the app UI.
- Same DB drives both backends: ST-LINK gets `-c port=SWD sn=...`; J-Link gets
  `device <part>`.

### 4. Other production niceties
- Log every flash to a text/CSV file (timestamp, board, file, probe, PASS/FAIL) for traceability.
- Export the "Boards programmed" counter to CSV.
- Option bytes / read-out protection (RDP) lock helper for production.
