import socket
import errno

def is_host_alive(ip, port=135, timeout=1.0):
    """
    Checks if a host is alive by attempting a TCP connection to a specific port.
    Returns "Alive" if the connection succeeds or is refused (host is active),
    and "Dead" otherwise (timeout, unreachable, etc.).
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            err = s.connect_ex((ip, port))
            
            # If the connection succeeded (0) or was explicitly refused (ECONNREFUSED),
            # it indicates the host is powered on and responding.
            if err == 0 or err == errno.ECONNREFUSED:
                return "Alive"
            return "Dead"
    except (socket.timeout, TimeoutError):
        return "Dead"
    except OSError:
        return "Dead"

if __name__ == "__main__":
    target_ip = "192.168.203.14"
    target_port = 135  # RPC port, commonly open or responding on Windows PCs
    
    status = is_host_alive(target_ip, target_port)
    print(status)

