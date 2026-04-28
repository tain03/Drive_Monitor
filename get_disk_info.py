import os
import re
import csv
import json
import socket
import subprocess
import shutil
import time
from datetime import datetime

CONFIG_FILE = 'config.json'

CDI_EXE = 'DiskInfo64.exe'
CDI_OUT = 'DiskInfo.txt'

def create_default_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            "Process": "DefaultProcess",
            "Machine": "DefaultMachine",
            "PC": socket.gethostname(),
            "IP": "",
            "OutputPath": ""
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

def load_config():
    create_default_config()
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_local_ip():
    try:
        # Create a socket to find the local IP used for external connections
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())

def get_cpu_usage():
    try:
        out = subprocess.check_output('wmic cpu get loadpercentage', shell=True, text=True)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if len(lines) > 1:
            return lines[1]
    except Exception:
        pass
    return "N/A"

def get_boot_time():
    try:
        out = subprocess.check_output('wmic os get lastbootuptime', shell=True, text=True)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if len(lines) > 1:
            # Format: 20260428203434.500000+420
            dt_str = lines[1].split('.')[0]
            dt_obj = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
            return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return "N/A"

def run_crystal_disk_info():
    if os.path.exists(CDI_OUT):
        try:
            os.remove(CDI_OUT)
        except:
            pass
            
    # Run CrystalDiskInfo to generate the report
    subprocess.run([CDI_EXE, '/CopyExit'], check=True, shell=True)
    
    # Wait for the file to be generated
    timeout = 30
    start_time = time.time()
    while not os.path.exists(CDI_OUT):
        if time.time() - start_time > timeout:
            print("Error: DiskInfo.txt was not generated in time.")
            return False
        time.sleep(1)
        
    # Wait a moment to ensure the file is completely written
    time.sleep(2)
    return True

def parse_cdi_output():
    drives = []
    current_drive = {}
    
    try:
        with open(CDI_OUT, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(CDI_OUT, 'r', encoding='utf-16', errors='ignore') as f:
            lines = f.readlines()
            
    for line in lines:
        line = line.strip()
        
        if line.startswith('Model :'):
            if current_drive:
                drives.append(current_drive)
            current_drive = {'Model': line.split(':', 1)[1].strip()}
            
        elif line.startswith('Serial Number :'):
            current_drive['Serial Number'] = line.split(':', 1)[1].strip()
            
        elif line.startswith('Disk Size :'):
            # e.g., 120.0 GB (8.4/120.0/120.0/120.0)
            size_str = line.split(':', 1)[1].strip()
            current_drive['Capacity'] = size_str.split('(')[0].strip()
            
        elif line.startswith('Rotation Rate :'):
            val = line.split(':', 1)[1].strip()
            if 'SSD' in val:
                current_drive['Drive Type'] = 'SSD'
            elif 'RPM' in val:
                current_drive['Drive Type'] = 'HDD'
            else:
                current_drive['Drive Type'] = val
                
        elif line.startswith('Power On Hours :'):
            # e.g., 12605 hours
            current_drive['Power On Hours'] = line.split(':', 1)[1].strip().split()[0]
            
        elif line.startswith('Temperature :'):
            # e.g., 40 C (104 F)
            current_drive['Temperature (C)'] = line.split(':', 1)[1].strip().split()[0]
            
        elif line.startswith('Health Status :'):
            # e.g., Good (64 %) or Good
            val = line.split(':', 1)[1].strip()
            if '(' in val:
                status, pct = val.split('(')
                current_drive['Health Status'] = status.strip()
                current_drive['Health Percentage'] = pct.replace(')', '').strip()
            else:
                current_drive['Health Status'] = val
                current_drive['Health Percentage'] = '100 %' if 'Good' in val else 'N/A'
                
        elif line.startswith('Drive Letter :'):
            current_drive['Drive Letter'] = line.split(':', 1)[1].strip()
            
    if current_drive:
        drives.append(current_drive)
        
    return drives

def calculate_free_space(drive_letters_str):
    if not drive_letters_str:
        return "N/A"
        
    letters = drive_letters_str.split()
    total_free_bytes = 0
    valid_drives = 0
    
    for letter in letters:
        if len(letter) == 2 and letter.endswith(':'):
            try:
                usage = shutil.disk_usage(letter + '\\')
                total_free_bytes += usage.free
                valid_drives += 1
            except Exception:
                pass
                
    if valid_drives > 0:
        free_gb = total_free_bytes / (1024**3)
        return f"{free_gb:.1f} GB"
    return "N/A"

def main():
    print("Loading config...")
    config = load_config()
    
    ip_address = config.get("IP", "").strip()
    if not ip_address:
        ip_address = get_local_ip()
        
    print("Running CrystalDiskInfo...")
    if not run_crystal_disk_info():
        return
        
    print("Parsing output...")
    drives = parse_cdi_output()
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_date = now.strftime("%Y-%m-%d")
    date_suffix = now.strftime("%Y%m%d")
    
    output_dir = config.get("OutputPath", "").strip()
    output_filename = f'Hard_drive_summary_{date_suffix}.csv'
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_csv = os.path.join(output_dir, output_filename)
    else:
        output_csv = output_filename
    
    print("Getting system info...")
    cpu_usage = get_cpu_usage()
    boot_time = get_boot_time()
    
    headers = [
        "Time", "Date", "Process", "Machine", "PC", "IP", "Boot Time", 
        "CPU Usage (%)", "Drive Type", "Model", "Serial Number", "Drive Letter", 
        "Capacity", "Free Space", "Health Status", "Health Percentage", 
        "Temperature (C)", "Power On Hours"
    ]
    
    file_exists = os.path.isfile(output_csv)
    
    with open(output_csv, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
            
        for drive in drives:
            drive_letter = drive.get('Drive Letter', '')
            free_space = calculate_free_space(drive_letter)
            
            row = {
                "Time": current_time,
                "Date": current_date,
                "Process": config.get("Process", ""),
                "Machine": config.get("Machine", ""),
                "PC": config.get("PC", ""),
                "IP": ip_address,
                "Boot Time": boot_time,
                "CPU Usage (%)": cpu_usage,
                "Drive Type": drive.get("Drive Type", "N/A"),
                "Model": drive.get("Model", "N/A"),
                "Serial Number": drive.get("Serial Number", "N/A"),
                "Drive Letter": drive_letter,
                "Capacity": drive.get("Capacity", "N/A"),
                "Free Space": free_space,
                "Health Status": drive.get("Health Status", "N/A"),
                "Health Percentage": drive.get("Health Percentage", "N/A"),
                "Temperature (C)": drive.get("Temperature (C)", "N/A"),
                "Power On Hours": drive.get("Power On Hours", "N/A")
            }
            writer.writerow(row)
            
    print(f"Done! Results written to {output_csv}")

if __name__ == "__main__":
    main()
