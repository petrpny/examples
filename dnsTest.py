import socket
import subprocess
import re

# Define the list of IP addresses
ip_addresses = ["192.168.1.1", "8.8.8.8", "8.8.4.4", "1.1.1.1", "208.67.222.222", "208.67.220.220"]

# Function to perform DNS forward lookup
def dns_lookup(ip):
    try:
        # Perform forward DNS lookup
        host_info = socket.gethostbyaddr(ip)
        hostname = host_info[0]
        aliases = ", ".join(host_info[1]) if host_info[1] else "None"
        addresses = ", ".join(host_info[2])
        print(f"Host Name: {hostname}")
        print(f"Aliases: {aliases}")
        print(f"Addresses: {addresses}")
    except socket.herror:
        print(f"DNS lookup failed for {ip}")

# Function to perform reverse lookup using nslookup and parse output
def reverse_lookup(ip):
    try:
        # Run nslookup command
        result = subprocess.run(
            ["nslookup", ip],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse the output to extract the hostname (PTR record)
        output = result.stdout.strip()
        # Use regex to find the line with the hostname (e.g., "name = hostname")
        match = re.search(r"name\s*=\s*([^\s]+)", output)
        if match:
            hostname = match.group(1).rstrip(".")  # Remove trailing dot
            print(f"Reverse Lookup: {hostname}")
        else:
            print(f"Reverse Lookup: No PTR record found")
    except subprocess.CalledProcessError:
        print(f"Reverse lookup failed for {ip}")

# Loop through each IP address
for ip in ip_addresses:
    print(f"IP Address: {ip}")
    dns_lookup(ip)
    reverse_lookup(ip)
    print("------------------------")
