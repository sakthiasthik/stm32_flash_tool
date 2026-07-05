import subprocess
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import os

# ---- CHANGE THIS PATH ----
CLI_PATH = r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"

FLASH_ADDRESS = "0x08000000"

# -------------------------
# Get connected boards
# -------------------------
def get_serial_numbers():
    try:
        result = subprocess.run([CLI_PATH, "-l"], capture_output=True, text=True)
        sns = re.findall(r"ST-LINK SN\s*:\s*(\w+)", result.stdout)

        # REMOVE duplicates
        sns = list(set(sns))

        return sns
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return []

# --------- Refresh --------

def refresh_boards():
    sns = get_serial_numbers()

    menu = dropdown["menu"]
    menu.delete(0, "end")

    if sns:
        for sn in sns:
            menu.add_command(label=sn, command=lambda value=sn: selected_sn.set(value))
        selected_sn.set(sns[0])
    else:
        menu.add_command(label="No board found", command=lambda: selected_sn.set("No board found"))
        selected_sn.set("No board found")


# -------------------------
# Browse file (ELF, BIN, HEX)
# -------------------------
def browse_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("Firmware files", "*.elf *.bin *.hex")]
    )
    if file_path:
        file_path_var.set(file_path)

# -------------------------
# Flash selected board
# -------------------------
def flash():
    sn = selected_sn.get()
    file_path = file_path_var.get()

    if not sn or sn == "No board found":
        messagebox.showerror("Error", "No board selected")
        return

    if not file_path:
        messagebox.showerror("Error", "No file selected")
        return

    ext = os.path.splitext(file_path)[1].lower()

    # Build command
    cmd = [CLI_PATH, "-c", f"port=SWD sn={sn}", "-w", file_path]

    # Only BIN needs address
    if ext == ".bin":
        cmd.append(FLASH_ADDRESS)

    cmd.append("-g")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            messagebox.showinfo("Success", "Flashing completed successfully!")
        else:
            messagebox.showerror("Error", result.stderr)

    except Exception as e:
        messagebox.showerror("Error", str(e))

# -------------------------
# GUI
# -------------------------
root = tk.Tk()
root.title("STM32 Flasher")
root.geometry("420x220")

# Board selection
tk.Label(root, text="Select Board:").pack(pady=5)

serial_numbers = get_serial_numbers()

selected_sn = tk.StringVar()

# Ensure at least one value exists
if serial_numbers:
    default_value = serial_numbers[0]
else:
    default_value = "No board found"
    serial_numbers = ["No board found"]

selected_sn.set(default_value)

dropdown = tk.OptionMenu(root, selected_sn, default_value, *serial_numbers)
dropdown.pack()

# File selection
file_path_var = tk.StringVar()

tk.Button(root, text="Select Firmware", command=browse_file).pack(pady=10)
tk.Label(root, textvariable=file_path_var, wraplength=380).pack()

# Flash button
tk.Button(root, text="Flash", command=flash, bg="green", fg="white").pack(pady=15)

# Refresh button
tk.Button(root, text="Refresh Boards", command=refresh_boards).pack(pady=5)

root.mainloop()