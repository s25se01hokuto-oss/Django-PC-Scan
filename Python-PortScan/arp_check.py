import subprocess
import re

def is_host_alive_arp(ip):
    """
    Checks if a host is alive by parsing the Linux ARP cache.
    Executes 'arp -an' securely using subprocess.
    Returns "Alive" if a valid MAC address is associated with the IP,
    and "Dead" if the IP is missing, incomplete, or invalid.
    """
    try:
        # Run "arp -an" securely without shell=True
        result = subprocess.run(
            ["arp", "-an"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Iterate through the ARP cache lines
        for line in result.stdout.splitlines():
            # Match the IP in parentheses, e.g. (192.168.203.14)
            if f"({ip})" in line:
                # Check if the entry is incomplete (supporting multiple locales like <incomplete> or <不完全>)
                if "<" in line or "incomplete" in line:
                    return "Dead"
                
                # Verify that a valid MAC address is present in the line
                # Standard MAC regex allows for 1 or 2 hex digits per octet
                mac_pattern = r"(?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}"
                if re.search(mac_pattern, line):
                    return "Alive"
                    
        return "Dead"
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "Dead"

if __name__ == "__main__":
    target_ip = "192.168.203.14"
    status = is_host_alive_arp(target_ip)
    print(status)
