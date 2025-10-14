# utils.py
import ipaddress
from datetime import datetime
import os, subprocess, urllib.request, sys, time

def expand_ip_range(ip_range_str):
    """Expand '192.168.1.10-192.168.1.20' into list of IP strings.
    If single IP/hostname provided, returns [ip]."""
    s = ip_range_str.strip()
    if '-' in s:
        start_ip, end_ip = s.split('-')
        start_int = int(ipaddress.IPv4Address(start_ip.strip()))
        end_int = int(ipaddress.IPv4Address(end_ip.strip()))
        if end_int < start_int:
            start_int, end_int = end_int, start_int
        return [str(ipaddress.IPv4Address(i)) for i in range(start_int, end_int + 1)]
    else:
        return [s]

def now_iso():
    return datetime.utcnow().isoformat(sep=' ', timespec='seconds')

def is_windows():
    import platform
    return platform.system().lower().startswith('win')

# Npcap automatic installer (Windows)
def ensure_npcap_installed(prompt_user=True):
    """Checks for Npcap on Windows. If missing, downloads and installs it silently.
    Returns True if installed or not required (non-Windows), False if installation failed."""
    if not is_windows():
        return True
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\npcap") as _:
            return True
    except Exception:
        if not prompt_user:
            return False
        try:
            from urllib.parse import urljoin
        except:
            pass
        try:
            url = "https://nmap.org/npcap/dist/npcap-1.60.exe"  # fallback commonly available URL
        except Exception:
            url = "https://nmap.org/npcap/dist/npcap-1.60.exe"
        installer_path = os.path.join(os.getenv('TEMP') or '.', 'npcap_installer.exe')
        try:
            print(f"Downloading Npcap from {url} to {installer_path}...")
            urllib.request.urlretrieve(url, installer_path)
        except Exception as e:
            print("Failed to download Npcap:", e)
            return False
        try:
            # Run installer silently. This requires admin privileges.
            subprocess.run([installer_path, "/S"], check=False)
            time.sleep(3)
            # check again
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\npcap") as _:
                return True
        except Exception as e:
            print("Npcap install failed:", e)
            return False
