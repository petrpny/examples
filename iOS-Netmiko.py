import ipaddress
import os
import re
import subprocess
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# ==============================
# Configuration
# ==============================

SUBNET = '172.31.200.0/24'       # Default subnet to scan
SSH_USERNAME = 'root'             # SSH username
SSH_PASSWORD = 'PhilipsR00t!'     # SSH password
TELNET_PASSWORD = 'm3150'         # Telnet password
TELNET_SECRET = 'm3150e'          # Telnet enable password
OUTPUT_DIR = 'switch_outputs'     # Base directory for outputs

# Commands to run on each device
COMMANDS = [
    'show running-config',
    'show version',
    'show interfaces status',
    'show ip interface brief'
]

# ----------------------------------------------------------
# OPTIONAL: Run on specific devices instead of scanning subnet
# ----------------------------------------------------------
# To use this mode, comment out the SUBNET section inside main()
# and uncomment the SPECIFIC_DEVICES list below.
SPECIFIC_DEVICES = [
      '172.31.200.2',
      '172.31.200.3',
]


# ==============================
# Functions
# ==============================

def ping_host(ip):
    """Ping a host to check if it's reachable."""
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '1', str(ip)],
                                capture_output=True, text=True, timeout=2)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def sanitize_filename(name):
    """Remove invalid characters for file/folder names."""
    return re.sub(r'[^A-Za-z0-9_.-]', '_', name)


def get_hostname(conn):
    """Retrieve the hostname from the device."""
    try:
        output = conn.send_command('show running-config | include ^hostname', expect_string=r'#')
        if output and 'hostname' in output:
            # Example: "hostname Switch01"
            return output.split()[1].strip()
    except Exception:
        pass

    # Fallback: use device prompt (e.g. "Switch01#")
    prompt = conn.find_prompt()
    return prompt.rstrip('# >').strip()


def connect_device(ip, protocol='ssh'):
    """Attempt to connect to a device using SSH or Telnet."""
    device = {
        'host': str(ip),
        'timeout': 10,
        'conn_timeout': 10,
    }

    if protocol == 'ssh':
        device.update({
            'device_type': 'cisco_ios',
            'username': SSH_USERNAME,
            'password': SSH_PASSWORD,
            'secret': SSH_PASSWORD,
        })
    else:  # Telnet
        device.update({
            'device_type': 'cisco_ios_telnet',
            'password': TELNET_PASSWORD,
            'secret': TELNET_SECRET,
        })

    try:
        conn = ConnectHandler(**device)
        if protocol == 'telnet':
            conn.enable()
        return conn, None
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


# ==============================
# Main Function
# ==============================

def main():
    # Determine mode: subnet or specific devices
    if SPECIFIC_DEVICES:
        device_list = [ipaddress.ip_address(ip) for ip in SPECIFIC_DEVICES]
        print(f"Running on {len(device_list)} manually specified devices.")
    else:
        network = ipaddress.ip_network(SUBNET, strict=False)
        device_list = list(network.hosts())
        print(f"Scanning subnet: {SUBNET}")

    # Create timestamped output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(OUTPUT_DIR, timestamp)
    os.makedirs(output_dir, exist_ok=True)

    summary_file = os.path.join(output_dir, 'summary_all_commands.txt')
    with open(summary_file, 'w') as summary_f:
        summary_f.write(f"Summary of Commands Run on Devices\n")
        summary_f.write(f"Generated on: {datetime.now()}\n\n")

    successful_connections = 0

    for ip in device_list:
        ip_str = str(ip)
        print(f"\nChecking {ip_str}...")

        # Optional: skip unreachable hosts
        if not ping_host(ip_str):
            print(f"  {ip_str} not reachable via ping, skipping.")
            continue

        # Try SSH first
        conn, error = connect_device(ip_str, protocol='ssh')
        connection_type = 'SSH'

        # If SSH fails, try Telnet
        if conn is None:
            print(f"  SSH failed for {ip_str}: {error}. Trying Telnet...")
            conn, error = connect_device(ip_str, protocol='telnet')
            connection_type = 'Telnet'

        if conn is None:
            print(f"  Telnet failed for {ip_str}: {error}")
            continue

        try:
            print(f"  Connected to {ip_str} via {connection_type}")
            hostname = get_hostname(conn)
            safe_hostname = sanitize_filename(hostname)
            print(f"  Hostname: {hostname}")

            # Create per-device folder
            device_folder = os.path.join(output_dir, safe_hostname)
            os.makedirs(device_folder, exist_ok=True)

            # Per-device output file
            hostname_file = os.path.join(device_folder, f"{safe_hostname}.txt")
            with open(hostname_file, 'w') as host_f:
                host_f.write(f"Output for {hostname} ({ip_str}) via {connection_type}\n")
                host_f.write(f"Generated on: {datetime.now()}\n\n")

                all_outputs = []
                for cmd in COMMANDS:
                    print(f"    Running: {cmd}")
                    output = conn.send_command(cmd, expect_string=r'#')
                    host_f.write(f"Command: {cmd}\n")
                    host_f.write("-" * 50 + "\n")
                    host_f.write(output + "\n\n")
                    all_outputs.append(f"\n--- {hostname} ({ip_str}, {connection_type}) ---\nCommand: {cmd}\n{output}")

                with open(summary_file, 'a') as summary_f:
                    summary_f.writelines(all_outputs)
                    summary_f.write("\n" + "=" * 80 + "\n")

            conn.disconnect()
            successful_connections += 1
            print(f"  Completed {hostname} ({ip_str})")

        except Exception as e:
            print(f"  Error processing {ip_str}: {e}")
            try:
                conn.disconnect()
            except Exception:
                pass

    print(f"\nScript completed. Processed {successful_connections} devices.")
    print(f"Outputs saved in: {output_dir}")
    print(f"Summary file: {summary_file}")


# ==============================
# Run
# ==============================
if __name__ == "__main__":
    main()