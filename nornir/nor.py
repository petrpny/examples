from nornir import InitNornir
import logging

# Keep Python logging for debug
logging.basicConfig(level=logging.DEBUG)

try:
    # Disable Nornir's logging to avoid conflict
    nr = InitNornir(config_file="config.yaml", logging={"enabled": False})
    print("Success! Hosts loaded into Nornir inventory:", nr.inventory.hosts.keys())
    
    print("\nDetailed host info:")
    for host in nr.inventory.hosts.values():
        print(f"{host.name}:")
        print(f"  - hostname: {host.hostname}")
        print(f"  - platform: {host.platform}")
        print(f"  - groups: {host.groups}")
        print(f"  - username: {host.username}")
        print(f"  - password: {'*' * len(host.password) if host.password else 'Not set (using key)'}")
        print(f"  - data keys: {sorted(host.data.keys())}")
    
    # Ansible validation
    import subprocess
    result = subprocess.run(["ansible-inventory", "-i", "inventory", "--list"], 
                           capture_output=True, text=True, cwd="/Users/PetrAir/examples")
    print("\nAnsible inventory validation:", "OK" if result.returncode == 0 else f"Failed: {result.stderr.strip()}")
    
except Exception as e:
    print(f"Error initializing inventory: {type(e).__name__}: {e}")
    print("\nDebug tips:")
    print("- Ensure 'hostsfile: inventory' is in config.yaml.")
    print("- Run 'ansible-inventory -i inventory --list' to check file.")
    print("- Verify Nornir version: pip show nornir (should be 3.x).")
