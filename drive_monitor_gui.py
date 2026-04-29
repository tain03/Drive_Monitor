import os
import re
import csv
import json
import socket
import subprocess
import shutil
import time
import sys
import ctypes
import winreg
from datetime import datetime, timedelta
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
CONFIG_FILE = os.path.join(BASE_PATH, 'config.json')
CDI_EXE = os.path.join(BASE_PATH, 'DiskInfo64.exe')
CDI_OUT = os.path.join(BASE_PATH, 'DiskInfo.txt')
LOG_FILE = os.path.join(BASE_PATH, 'app_error.log')
APP_NAME = "CDI_Drive_Monitor"
INTERVAL_SECONDS = 300  # 5 minutes

def log_error(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

def add_to_startup():
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = os.path.realpath(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0])
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Failed to add to startup: {e}")

# --- Logic from previous script ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            "Process": "DefaultProcess",
            "Machine": "DefaultMachine",
            "Model": "DefaultModel",
            "PC": socket.gethostname(),
            "IP": "",
            "LotID": "000000000000",
            "OutputPath": ""
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    
    try:
        # Try utf-8-sig first to handle UTF-8 with BOM
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except (UnicodeDecodeError, json.JSONDecodeError):
        try:
            # Fallback to utf-16 if utf-8 fails
            with open(CONFIG_FILE, 'r', encoding='utf-16') as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Failed to load config even with utf-16: {e}")
            raise e

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return socket.gethostbyname(socket.gethostname())

def get_cpu_usage():
    try:
        out = subprocess.check_output('wmic cpu get loadpercentage', shell=True, text=True)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if len(lines) > 1: return lines[1]
    except: pass
    return "N/A"

def get_boot_time():
    try:
        out = subprocess.check_output('wmic os get lastbootuptime', shell=True, text=True)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if len(lines) > 1:
            dt_str = lines[1].split('.')[0]
            dt_obj = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
            return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    except: pass
    return "N/A"

def run_cdi_and_parse():
    if os.path.exists(CDI_OUT):
        try: os.remove(CDI_OUT)
        except: pass
    
    if not os.path.exists(CDI_EXE):
        return None, f"Error: {CDI_EXE} not found."

    try:
        # Use a single string for the command when shell=True on Windows
        cmd = f'"{CDI_EXE}" /CopyExit'
        subprocess.run(cmd, check=True, shell=True, cwd=BASE_PATH)
        
        # Wait for file
        for _ in range(30):
            if os.path.exists(CDI_OUT): break
            time.sleep(1)
        else:
            return None, "Error: DiskInfo.txt not generated."
        
        time.sleep(2)
        
        # Parse
        drives = []
        current_drive = {}
        try:
            with open(CDI_OUT, 'r', encoding='utf-8') as f: lines = f.readlines()
        except UnicodeDecodeError:
            with open(CDI_OUT, 'r', encoding='utf-16', errors='ignore') as f: lines = f.readlines()

        for line in lines:
            line = line.strip()
            if line.startswith('Model :'):
                if current_drive: drives.append(current_drive)
                current_drive = {'Model': line.split(':', 1)[1].strip()}
            elif line.startswith('Serial Number :'): current_drive['Serial Number'] = line.split(':', 1)[1].strip()
            elif line.startswith('Disk Size :'):
                val = line.split(':', 1)[1].strip().split('(')[0].strip()
                current_drive['Capacity'] = val.replace('GB', '').strip()
            elif line.startswith('Rotation Rate :'):
                val = line.split(':', 1)[1].strip()
                current_drive['Drive Type'] = 'SSD' if 'SSD' in val else ('HDD' if 'RPM' in val else val)
            elif line.startswith('Power On Hours :'): current_drive['Power On Hours'] = line.split(':', 1)[1].strip().split()[0]
            elif line.startswith('Temperature :'): current_drive['Temperature (C)'] = line.split(':', 1)[1].strip().split()[0]
            elif line.startswith('Health Status :'):
                val = line.split(':', 1)[1].strip()
                if '(' in val:
                    status, pct = val.split('(')
                    current_drive['Health Status'] = status.strip()
                    current_drive['Health Percentage'] = pct.replace(')', '').replace('%', '').strip()
                else:
                    current_drive['Health Status'] = val
                    current_drive['Health Percentage'] = '100' if 'Good' in val else 'N/A'
            elif line.startswith('Drive Letter :'): current_drive['Drive Letter'] = line.split(':', 1)[1].strip()
        
        if current_drive: drives.append(current_drive)
        return drives, None
    except Exception as e:
        return None, str(e)

def calculate_free_space(drive_letters_str):
    if not drive_letters_str: return "N/A"
    letters = drive_letters_str.split()
    total_free = 0
    count = 0
    for l in letters:
        if len(l) == 2 and l.endswith(':'):
            try:
                total_free += shutil.disk_usage(l + '\\').free
                count += 1
            except: pass
    return f"{total_free / (1024**3):.1f}" if count > 0 else "N/A"

# --- GUI Application ---
class DriveMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Drive Health Monitor")
        self.root.geometry("500x480")
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.config = load_config()
        self.countdown = INTERVAL_SECONDS
        self.is_running = True
        
        self.setup_ui()
        self.setup_tray()
        self.update_info()
        self.tick()
        
        # Initial run
        threading.Thread(target=self.perform_logging, daemon=True).start()

    def setup_ui(self):
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Hard Drive Monitoring System", style="Header.TLabel").pack(pady=(0, 20))

        fields = [
            ("Model:", "Model"),
            ("Process:", "Process"),
            ("Machine:", "Machine"),
            ("PC:", "PC"),
            ("IP:", "IP"),
            ("Output Path:", "OutputPath")
        ]

        self.labels = {}
        for text, key in fields:
            f = ttk.Frame(main_frame)
            f.pack(fill=tk.X, pady=3)
            ttk.Label(f, text=text, width=15, anchor=tk.W).pack(side=tk.LEFT)
            lbl = ttk.Label(f, text="Loading...", font=("Segoe UI", 10, "bold"), wraplength=300)
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.labels[key] = lbl

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)

        self.timer_label = ttk.Label(main_frame, text="Next update in: 05:00", font=("Segoe UI", 14, "bold"), foreground="#2c3e50")
        self.timer_label.pack(pady=10)

        self.status_label = ttk.Label(main_frame, text="Status: Ready", font=("Segoe UI", 9, "italic"))
        self.status_label.pack(side=tk.BOTTOM, anchor=tk.W)

    def update_info(self):
        self.config = load_config()
        ip = self.config.get("IP", "").strip() or get_local_ip()
        
        self.labels["Model"].config(text=self.config.get("Model", "N/A"))
        self.labels["Process"].config(text=self.config.get("Process", "N/A"))
        self.labels["Machine"].config(text=self.config.get("Machine", "N/A"))
        self.labels["PC"].config(text=self.config.get("PC", socket.gethostname()))
        self.labels["IP"].config(text=ip)
        self.labels["OutputPath"].config(text=self.config.get("OutputPath", "Current Folder") or "Current Folder")

    def tick(self):
        if self.countdown <= 0:
            self.countdown = INTERVAL_SECONDS
            threading.Thread(target=self.perform_logging, daemon=True).start()
        
        mins, secs = divmod(self.countdown, 60)
        self.timer_label.config(text=f"Next update in: {mins:02d}:{secs:02d}")
        self.countdown -= 1
        self.root.after(1000, self.tick)

    def perform_logging(self):
        self.status_label.config(text="Status: Collecting data...")
        self.root.update_idletasks()
        
        drives, err = run_cdi_and_parse()
        if err:
            self.status_label.config(text=f"Status: Error - {err}")
            return

        config = load_config()
        ip = config.get("IP", "").strip() or get_local_ip()
        now = datetime.now()
        
        output_dir = config.get("OutputPath", "").strip()
        lot_id = config.get("LotID", "000000000000").strip()
        filename = f"{lot_id}_{now.strftime('%Y%m%d')}_Hard_drive_summary.csv"
        
        if output_dir:
            try:
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, filename)
            except Exception as e:
                log_error(f"Failed to create output dir {output_dir}: {e}")
                output_path = os.path.join(BASE_PATH, filename)
        else:
            output_path = os.path.join(BASE_PATH, filename)
        
        headers = ["Time", "Process", "Machine", "PC", "IP", "Model", "Boot Time", "CPU Usage (%)", "Drive Type", "Drive Model", "Serial Number", "Drive Letter", "Capacity(GB)", "Free Space(GB)", "Health Percentage (%)", "Temperature (C)", "Power On Hours"]
        
        try:
            file_exists = os.path.isfile(output_path)
            with open(output_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists: writer.writeheader()
                
                cpu = get_cpu_usage()
                boot = get_boot_time()
                
                for d in drives:
                    row = {
                        "Time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "Process": config.get("Process", ""),
                        "Machine": config.get("Machine", ""),
                        "PC": config.get("PC", ""),
                        "IP": ip,
                        "Model": config.get("Model", ""),
                        "Boot Time": boot,
                        "CPU Usage (%)": cpu,
                        "Drive Type": d.get("Drive Type", "N/A"),
                        "Drive Model": d.get("Model", "N/A"),
                        "Serial Number": d.get("Serial Number", "N/A"),
                        "Drive Letter": d.get("Drive Letter", ""),
                        "Capacity(GB)": d.get("Capacity", "N/A"),
                        "Free Space(GB)": calculate_free_space(d.get("Drive Letter", "")),
                        "Health Percentage (%)": d.get("Health Percentage", "N/A"),
                        "Temperature (C)": d.get("Temperature (C)", "N/A"),
                        "Power On Hours": d.get("Power On Hours", "N/A")
                    }
                    writer.writerow(row)
            self.status_label.config(text=f"Status: Last update at {now.strftime('%H:%M:%S')}")
        except Exception as e:
            self.status_label.config(text=f"Status: Write Error - {str(e)}")

    def hide_window(self):
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()

    def quit_app(self, icon, item):
        self.is_running = False
        icon.stop()
        self.root.quit()

    def setup_tray(self):
        # Generate a simple icon
        image = Image.new('RGB', (64, 64), color=(41, 128, 185))
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill=(236, 240, 241))
        
        menu = (item('Show Monitor', self.show_window), item('Exit', self.quit_app))
        self.tray_icon = pystray.Icon("CDI Monitor", image, "Drive Health Monitor", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

if __name__ == "__main__":
    try:
        if not is_admin():
            run_as_admin()
        else:
            add_to_startup()
            root = tk.Tk()
            app = DriveMonitorApp(root)
            root.mainloop()
    except Exception as e:
        log_error(f"CRITICAL ERROR: {str(e)}")
        import traceback
        log_error(traceback.format_exc())
