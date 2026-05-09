import os
import socket
import sys
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
NMAP_PATH: str | None = os.getenv("NMAP_PATH", "nmap")

# TOOL 1: Check SSH connectivity
def check_ssh_connectivity(ip:str):
    """
    Checks SSH connectivity to an instance
    """
    port=22
    timeout=5
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            print(f"SUCCESS: Port {port} is open on {ip}")
            return True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"FAILURE: Cannot reach {ip} on port {port}. Error: {e}")
        return False

# TOOL 2: Scan network ports
def scan_ports(ip: str):
    """
    Scans network ports on compute instane to determine if the ports are open or closed 
    """
    result = subprocess.run(
            [NMAP_PATH, "--top-ports", "25", "-Pn", ip],
            capture_output=True, 
            text=True,
            timeout=40)

    print(result.stdout)
    return result.stdout
