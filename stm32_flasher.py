#!/usr/bin/env python3
"""
STM32 Flash Tool — Lightweight, cross-platform flash programmer.
Single file. Zero dependencies (stdlib only).
Double-click to run. Packages into standalone .exe / binary via PyInstaller.

Requires: STM32CubeProgrammer CLI installed separately.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: BOOTSTRAP — runs before GUI imports
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import os
import subprocess
import platform
import shutil
from pathlib import Path

CONFIG_FILE = os.path.expanduser("~/.stm32flasher.json")
CLI_NAME = "STM32_Programmer_CLI.exe" if platform.system() == "Windows" else "STM32_Programmer_CLI"

def _bootstrap():
    """Check and fix prerequisites. Returns detected CLI path or None."""

    # 1. Python version
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or newer required.")
        print(f"Current: Python {sys.version_info.major}.{sys.version_info.minor}")
        print("Install from: https://python.org")
        sys.exit(1)

    # 2. Check tkinter (must work before we import it)
    try:
        import tkinter  # noqa: F401
    except ImportError:
        if platform.system() == "Linux":
            print("tkinter not found. Attempting auto-install...")
            if _install_tkinter_linux():
                print("Installed! Restarting...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print("ERROR: Could not install python3-tk automatically.")
                print("Manual: sudo apt install python3-tk")
                print("      : sudo dnf install python3-tkinter")
                print("      : sudo pacman -S tk")
                sys.exit(1)
        else:
            print("ERROR: tkinter not found.")
            print("Reinstall Python and ensure 'tcl/tk and IDLE' is checked.")
            print("Download: https://python.org")
            sys.exit(1)

    # 3. Find STM32_Programmer_CLI
    cli = _load_cli_from_config() or _detect_cli()

    if cli:
        print(f"STM32_Programmer_CLI: {cli}")
    else:
        print("WARNING: STM32_Programmer_CLI not found.")
        print("Install STM32CubeProgrammer: https://www.st.com/en/development-tools/stm32cubeprog.html")
        print("The app will launch — set the CLI path in the GUI.")

    return cli


def _install_tkinter_linux():
    """Try to install python3-tk on Linux. Returns True on success."""
    methods = [
        ["pkexec", "apt-get", "install", "-y", "python3-tk"],
        ["sudo", "apt-get", "install", "-y", "python3-tk"],
        ["pkexec", "dnf", "install", "-y", "python3-tkinter"],
        ["sudo", "dnf", "install", "-y", "python3-tkinter"],
        ["pkexec", "pacman", "-S", "--noconfirm", "tk"],
        ["sudo", "pacman", "-S", "--noconfirm", "tk"],
    ]
    for cmd in methods:
        if shutil.which(cmd[0]) is None:
            continue
        try:
            print(f"  Trying: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, timeout=120)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError, PermissionError):
            continue
    return False


def _load_cli_from_config():
    """Load saved CLI path from config file."""
    import json
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
            path = data.get("cli_path", "")
            if path and os.path.isfile(path):
                return path
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    return None


def _detect_cli():
    """Search for STM32_Programmer_CLI on the system."""

    # Check PATH first
    found = shutil.which(CLI_NAME)
    if found:
        return found

    system = platform.system()

    if system == "Linux":
        candidates = [
            "/usr/local/STMicroelectronics/STM32Cube/STM32CubeProgrammer/bin/STM32_Programmer_CLI",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

        # Search /opt/st recursively (where STM32CubeIDE puts it)
        try:
            matches = list(Path("/opt/st").rglob("STM32_Programmer_CLI"))
            if matches:
                # Prefer shortest path (usually the standalone install)
                matches.sort(key=lambda p: len(str(p)))
                for m in matches:
                    if os.access(m, os.X_OK):
                        return str(m)
        except PermissionError:
            pass

    elif system == "Windows":
        candidates = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"),
                         "STMicroelectronics", "STM32Cube", "STM32CubeProgrammer",
                         "bin", "STM32_Programmer_CLI.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
                         "STMicroelectronics", "STM32Cube", "STM32CubeProgrammer",
                         "bin", "STM32_Programmer_CLI.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

    return None


# Run bootstrap now — before any tkinter imports
_detected_cli_path = _bootstrap()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: IMPORTS (safe — bootstrap ensured tkinter exists)
# ═══════════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import re
import queue

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: APPLICATION CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class STM32Flasher(tk.Tk):
    """Main application window."""

    FLASH_ADDRESS_DEFAULT = "0x08000000"
    TIMEOUT_SECONDS = 120

    def __init__(self, cli_path=None):
        super().__init__()

        self.title("STM32 Flash Tool")
        self.geometry("480x320")
        self.resizable(True, True)
        self.minsize(420, 280)

        # Set window icon (cross-platform)
        try:
            if getattr(sys, 'frozen', False):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base, "icon.png")
            if os.path.isfile(icon_path):
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception:
            pass  # icon is optional, non-critical

        # State
        self.cli_path = tk.StringVar(value=cli_path or "")
        self.selected_sn = tk.StringVar(value="")
        self.firmware_path = tk.StringVar()
        self.flash_address = tk.StringVar(value=self.FLASH_ADDRESS_DEFAULT)
        self.status_text = tk.StringVar(value="Ready")

        # Worker queue
        self._queue = queue.Queue()
        self._worker_thread = None
        self._busy = False

        # Config
        self._load_config()

        # Build UI
        self._build_ui()
        self._poll_queue()

        # Initial board scan (after UI is up)
        self.after(500, self.refresh_boards)

    # ── Config ────────────────────────────────────────────────────────────

    def _load_config(self):
        """Load saved settings from JSON config file."""
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        if not self.cli_path.get():
            self.cli_path.set(data.get("cli_path", ""))
        addr = data.get("flash_address", self.FLASH_ADDRESS_DEFAULT)
        self.flash_address.set(addr)

    def _save_config(self):
        """Persist current settings to JSON config file."""
        data = {
            "cli_path": self.cli_path.get(),
            "flash_address": self.flash_address.get(),
            "last_dir": os.path.dirname(self.firmware_path.get()) if self.firmware_path.get() else "",
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass  # non-fatal

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        """Create all widgets."""
        pad = {"padx": 12, "pady": 4}

        # -- CLI path row --
        cli_frame = ttk.Frame(self)
        cli_frame.pack(fill="x", **pad)
        ttk.Label(cli_frame, text="CLI:").pack(side="left")
        self._cli_label = ttk.Label(cli_frame, text="", foreground="gray")
        self._cli_label.pack(side="left", padx=4)
        ttk.Button(cli_frame, text="Set...", command=self._browse_cli,
                   width=6).pack(side="right")
        self._update_cli_label()

        # -- Board selection --
        board_frame = ttk.Frame(self)
        board_frame.pack(fill="x", **pad)
        ttk.Label(board_frame, text="Board:").pack(side="left")
        self._board_combo = ttk.Combobox(board_frame, textvariable=self.selected_sn,
                                         state="readonly", width=30)
        self._board_combo.pack(side="left", padx=4, fill="x", expand=True)
        self._btn_refresh = ttk.Button(board_frame, text="Refresh",
                                       command=self.refresh_boards, width=8)
        self._btn_refresh.pack(side="right")

        # -- File selection --
        file_frame = ttk.Frame(self)
        file_frame.pack(fill="x", **pad)
        ttk.Label(file_frame, text="File:").pack(side="left")
        self._file_entry = ttk.Entry(file_frame, textvariable=self.firmware_path)
        self._file_entry.pack(side="left", padx=4, fill="x", expand=True)
        self._btn_browse = ttk.Button(file_frame, text="Browse",
                                      command=self._browse_file, width=8)
        self._btn_browse.pack(side="right")

        # -- Flash address (for BIN files) --
        addr_frame = ttk.Frame(self)
        addr_frame.pack(fill="x", **pad)
        ttk.Label(addr_frame, text="Addr:").pack(side="left")
        self._addr_entry = ttk.Entry(addr_frame, textvariable=self.flash_address,
                                     width=14)
        self._addr_entry.pack(side="left", padx=4)
        ttk.Label(addr_frame, text="(BIN only)", foreground="gray").pack(side="left")
        # Track file changes to grey out address for non-BIN
        self.firmware_path.trace_add("write", self._on_file_changed)

        # Separator
        ttk.Separator(self).pack(fill="x", padx=12, pady=8)

        # -- Flash + Verify button (big) --
        self._btn_flash = ttk.Button(self, text="FLASH + VERIFY",
                                     command=self.flash_and_verify)
        self._btn_flash.pack(pady=(8, 2))
        # Make it bigger with a custom style
        style = ttk.Style()
        style.configure("Big.TButton", font=("", 12, "bold"))
        self._btn_flash.configure(style="Big.TButton")

        # -- Verify Only button (small) --
        self._btn_verify = ttk.Button(self, text="Verify Only",
                                      command=self.verify_only)
        self._btn_verify.pack(pady=2)

        # -- Status --
        self._status_label = tk.Label(self, textvariable=self.status_text,
                                      font=("", 14, "bold"), fg="black")
        self._status_label.pack(pady=(10, 4))

        # -- Progress output (hidden by default) --
        self._output_text = tk.Text(self, height=4, state="disabled",
                                    font=("Consolas", 9), bg="#f5f5f5")
        # Not packed by default — shown during operations

    def _update_cli_label(self):
        """Update the CLI path display."""
        p = self.cli_path.get()
        if p and os.path.isfile(p):
            self._cli_label.configure(text=os.path.basename(p), foreground="green")
        elif p:
            self._cli_label.configure(text="Not found", foreground="red")
        else:
            self._cli_label.configure(text="Not set", foreground="gray")

    # ── Button State ──────────────────────────────────────────────────────

    def _set_busy(self, busy):
        """Enable/disable controls during operations."""
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._btn_flash.configure(state=state)
        self._btn_verify.configure(state=state)
        self._btn_refresh.configure(state=state)
        self._btn_browse.configure(state=state)
        self._addr_entry.configure(state=state)

    # ── Actions ───────────────────────────────────────────────────────────

    def refresh_boards(self):
        """Scan for connected ST-LINK probes (runs in background thread)."""
        cli = self.cli_path.get()
        if not cli or not os.path.isfile(cli):
            # Try re-detection
            found = _detect_cli()
            if found:
                self.cli_path.set(found)
                self._save_config()
                self._update_cli_label()
            else:
                messagebox.showwarning("CLI Not Found",
                    "STM32_Programmer_CLI not found.\n\n"
                    "Install STM32CubeProgrammer or set the CLI path manually.")
                return

        def _scan():
            try:
                proc = subprocess.run(
                    [cli, "-l"],
                    capture_output=True, text=True, timeout=15
                )
                output = proc.stdout + proc.stderr
                # Parse serial numbers
                sns = re.findall(r"ST-LINK SN\s*:\s*(\S+)", output)
                sns = list(dict.fromkeys(sns))  # dedupe, preserve order
                self._queue.put(("boards", sns))
            except subprocess.TimeoutExpired:
                self._queue.put(("error", "Board scan timed out."))
            except FileNotFoundError:
                self._queue.put(("error", f"CLI not found: {cli}"))
            except Exception as e:
                self._queue.put(("error", str(e)))

        self._set_busy(True)
        self.status_text.set("Scanning for boards...")
        self._status_label.configure(fg="black")
        self._btn_refresh.configure(state="disabled")
        threading.Thread(target=_scan, daemon=True).start()

    def _browse_file(self):
        """Open file dialog for firmware selection."""
        path = filedialog.askopenfilename(
            title="Select Firmware",
            filetypes=[("Firmware", "*.elf *.bin *.hex"), ("All files", "*.*")],
        )
        if path:
            self.firmware_path.set(path)
            self._save_config()

    def _browse_cli(self):
        """Manually set CLI path via file dialog."""
        if platform.system() == "Windows":
            filters = [("Executable", "*.exe"), ("All files", "*.*")]
        else:
            filters = [("Executable", "*"), ("All files", "*.*")]

        path = filedialog.askopenfilename(
            title="Select STM32_Programmer_CLI",
            filetypes=filters,
        )
        if path and os.path.isfile(path):
            self.cli_path.set(path)
            self._update_cli_label()
            self._save_config()
            self.refresh_boards()

    def _on_file_changed(self, *_):
        """Grey out address field when file is not .bin."""
        path = self.firmware_path.get()
        ext = os.path.splitext(path)[1].lower() if path else ""
        if ext == ".bin":
            self._addr_entry.configure(state="normal")
        else:
            self._addr_entry.configure(state="disabled")

    # ── Flash + Verify ────────────────────────────────────────────────────

    def flash_and_verify(self):
        """Write firmware + verify + run (primary production button)."""
        self._run_operation(
            mode="flash_verify",
            label="Flash+Verify",
            build_cmd=self._build_flash_verify_cmd,
        )

    def verify_only(self):
        """Verify only — re-check an already-flashed chip."""
        self._run_operation(
            mode="verify",
            label="Verify",
            build_cmd=self._build_verify_only_cmd,
        )

    def _build_base_args(self):
        """Return [cli, -c, port=SWD sn=XXX] or None if validation fails."""
        sn = self.selected_sn.get()
        file_path = self.firmware_path.get()
        cli = self.cli_path.get()

        if not sn or sn == "No board found":
            messagebox.showerror("Error", "No board selected. Click Refresh to scan.")
            return None
        if not file_path:
            messagebox.showerror("Error", "No firmware file selected.")
            return None
        if not cli or not os.path.isfile(cli):
            messagebox.showerror("Error", "STM32_Programmer_CLI not found.\nSet the CLI path first.")
            return None

        cmd = [cli, "-c", f"port=SWD sn={sn}"]
        return cmd, file_path

    def _build_flash_verify_cmd(self):
        """Build command: write + verify + run."""
        base = self._build_base_args()
        if base is None:
            return None
        cmd, file_path = base

        cmd.extend(["-w", file_path])

        # Address only for BIN files
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".bin":
            cmd.append(self.flash_address.get())

        cmd.extend(["-v", "-g"])
        return cmd

    def _build_verify_only_cmd(self):
        """Build command: verify only (no write, no run)."""
        base = self._build_base_args()
        if base is None:
            return None
        cmd, file_path = base

        cmd.extend(["-v", file_path])

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".bin":
            cmd.append(self.flash_address.get())

        return cmd

    def _run_operation(self, mode, label, build_cmd):
        """Generic: validate, build command, launch thread."""
        cmd = build_cmd()
        if cmd is None:
            return

        if self._busy:
            return

        self._set_busy(True)
        self.status_text.set(f"{label} in progress...")
        self._status_label.configure(fg="black")
        self._show_output()

        def _worker():
            self._queue.put(("log", f">>> {' '.join(cmd)}\n"))
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                for line in proc.stdout:
                    self._queue.put(("log", line))
                proc.wait(timeout=self.TIMEOUT_SECONDS)

                if proc.returncode == 0:
                    self._queue.put(("done", mode, proc.returncode, ""))
                else:
                    self._queue.put(("done", mode, proc.returncode,
                                     f"CLI exited with code {proc.returncode}"))
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
                self._queue.put(("done", mode, -1, "Operation timed out."))
            except FileNotFoundError:
                self._queue.put(("done", mode, -1,
                                 f"CLI not found: {self.cli_path.get()}"))
            except Exception as e:
                self._queue.put(("done", mode, -1, str(e)))

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()

    # ── Queue Polling ─────────────────────────────────────────────────────

    def _poll_queue(self):
        """Check worker queue every 100ms and update UI."""
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle_message(self, msg):
        """Process a message from the worker thread."""
        kind = msg[0]

        if kind == "boards":
            sns = msg[1]
            if sns:
                self._board_combo["values"] = sns
                self.selected_sn.set(sns[0])
                self.status_text.set(f"Found {len(sns)} board(s)")
                self._status_label.configure(fg="green")
            else:
                self._board_combo["values"] = ["No board found"]
                self.selected_sn.set("No board found")
                self.status_text.set("No board found — check USB connection")
                self._status_label.configure(fg="red")
            self._set_busy(False)

        elif kind == "error":
            self.status_text.set(str(msg[1]))
            self._status_label.configure(fg="red")
            self._set_busy(False)

        elif kind == "log":
            self._append_output(msg[1])

        elif kind == "done":
            mode, rc, err = msg[1], msg[2], msg[3]
            self._set_busy(False)

            if mode == "flash_verify":
                verb = "flashed + verified"
            else:
                verb = "verified"

            if rc == 0:
                self.status_text.set(f"PASS — {verb} successfully")
                self._status_label.configure(fg="green")
                self._save_config()
            else:
                self.status_text.set(f"FAIL — {err}")
                self._status_label.configure(fg="red")

            self._append_output(f"\n--- {self.status_text.get()} ---\n")

    # ── Output Text Widget ────────────────────────────────────────────────

    def _show_output(self):
        """Show the output text widget."""
        self._output_text.configure(state="normal")
        self._output_text.delete("1.0", "end")
        self._output_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    def _append_output(self, text):
        """Append a line to the output widget."""
        self._output_text.configure(state="normal")
        self._output_text.insert("end", text)
        self._output_text.see("end")
        self._output_text.configure(state="disabled")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = STM32Flasher(cli_path=_detected_cli_path)
    app.mainloop()


if __name__ == "__main__":
    main()
