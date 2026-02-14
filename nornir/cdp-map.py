from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config
from nornir_utils.plugins.functions import print_result, print_title
import logging
import subprocess
import json

# Set logging to INFO
logging.basicConfig(level=logging.INFO)

def cdp_map(task):
    """Task to fetch CDP neighbors and configure interface descriptions."""
    changed = False  # Track changes
    try:
        # Ensure platform for Netmiko
        if not task.host.platform:
            task.host.platform = 'cisco_ios'
        
        # SSH connection parameters
        connection_params = {
            'device_type': 'cisco_ios_ssh',
            'ssh_config_file': None,
            'allow_agent': False,
            'hostkey_verify': False,
            'session_config': {
                'HostKeyAlgorithms': 'ssh-rsa',
                'KexAlgorithms': 'diffie-hellman-group1-sha1',
                'Ciphers': 'aes256-cbc,3des-cbc',
                'MACs': 'hmac-md5,hmac-sha2-512'
            },
            'conn_timeout': 10,
            'auth_timeout': 10,
        }
        
        # Try Genie parsing
        r = task.run(
            task=netmiko_send_command,
            name="Fetch CDP Neighbors",
            command_string="show cdp neighbors",
            use_genie=True
        )
        task.host["facts"] = r.result
        logging.debug(f"{task.host.name}: Raw Genie output: {r.result}")
        
        # Check Genie output
        outer = task.host["facts"]
        if not outer or 'cdp' not in outer or 'index' not in outer.get('cdp', {}):
            print(f"{task.host.name}: Genie parsing failed, trying TextFSM")
            # Fallback to TextFSM
            r = task.run(
                task=netmiko_send_command,
                name="Fetch CDP Neighbors (TextFSM)",
                command_string="show cdp neighbors",
                use_textfsm=True
            )
            task.host["facts"] = r.result
            logging.debug(f"{task.host.name}: Raw TextFSM output: {r.result}")
            outer = task.host["facts"]
            if not outer or not isinstance(outer, list):
                print(f"{task.host.name}: No CDP neighbors found or parsing failed")
                task.result = {"changed": changed}
                return
            
            # Process TextFSM output
            for neighbor in outer:
                local_intf = neighbor.get('local_interface')
                remote_port = neighbor.get('neighbor_interface')
                remote_id = neighbor.get('neighbor_name')
                if local_intf and remote_port and remote_id:
                    logging.info(f"{task.host.name}: Parsed neighbor: {remote_id} on {local_intf} -> {remote_port}")
                    config_commands = [
                        f"interface {local_intf}",
                        f"description Connected to {remote_id} via its {remote_port} interface"
                    ]
                    result = task.run(
                        task=netmiko_send_config,
                        name=f"Configure {local_intf} Description",
                        config_commands=config_commands
                    )
                    if result.changed:
                        changed = True
            task.result = {"changed": changed}
            return
        
        # Process Genie output
        indexer = outer['cdp']['index']
        for idx in indexer:
            local_intf = indexer[idx]['local_interface']
            remote_port = indexer[idx]['port_id']
            remote_id = indexer[idx]['device_id']
            logging.info(f"{task.host.name}: Parsed neighbor: {remote_id} on {local_intf} -> {remote_port}")
            config_commands = [
                f"interface {local_intf}",
                f"description Connected to {remote_id} via its {remote_port} interface"
            ]
            result = task.run(
                task=netmiko_send_config,
                name=f"Configure {local_intf} Description",
                config_commands=config_commands
            )
            if result.changed:
                changed = True
        task.result = {"changed": changed}
    except Exception as e:
        print(f"{task.host.name}: Error in cdp_map: {type(e).__name__}: {e}")
        logging.error(f"{task.host.name}: Exception details: {e}")
        task.result = {"changed": changed, "error": str(e)}

try:
    # Initialize Nornir
    nr = InitNornir(config_file="config.yaml", logging={"enabled": False})
    
    # Parse Ansible inventory
    result = subprocess.run(["ansible-inventory", "-i", "inventory", "--list"], 
                           capture_output=True, text=True, cwd="/Users/PetrAir/examples/nornir")
    if result.returncode != 0:
        raise RuntimeError(f"Ansible inventory parse failed: {result.stderr}")
    
    ansible_inv = json.loads(result.stdout)
    logging.info(f"Ansible inventory output: {ansible_inv}")
    global_vars = ansible_inv.get('all', {}).get('vars', {})
    host_vars = ansible_inv.get('_meta', {}).get('hostvars', {})
    
    for host in nr.inventory.hosts.values():
        logging.info(f"Processing host {host.name}: current data keys {list(host.data.keys())}")
        for k, v in global_vars.items():
            if k not in host.data:
                host.data[k] = v
        host_specific_vars = host_vars.get(host.name, {})
        for k, v in host_specific_vars.items():
            host.data[k] = v
        if host.data.get('ansible_network_os') == 'cisco.ios.ios' or not host.platform:
            host.platform = 'cisco_ios'
        host.data['ansible_ssh_common_args'] = (
            "-o HostKeyAlgorithms=ssh-rsa "
            "-o KexAlgorithms=diffie-hellman-group1-sha1 "
            "-o Ciphers=aes256-cbc,3des-cbc "
            "-o MACs=hmac-md5,hmac-sha2-512"
        )
        logging.info(f"Updated host {host.name}: data keys {list(host.data.keys())}")
    
    # Print inventory
    print_title("Loaded Inventory")
    print(f"Hosts: {nr.inventory.hosts.keys()}")
    for host in nr.inventory.hosts.values():
        print(f"{host.name}:")
        print(f"  - hostname: {host.hostname}")
        print(f"  - platform: {host.platform}")
        print(f"  - groups: {host.groups}")
        print(f"  - username: {host.username}")
        print(f"  - password: {'*' * len(host.password) if host.password else 'Not set (using key)'}")
        print(f"  - data keys: {sorted(host.data.keys())}")
    
    # Run CDP task
    print_title("Running CDP Neighbor Mapping")
    results = nr.run(task=cdp_map)
    print_result(results)
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    print("\nDebug tips:")
    print("- Ensure 'hostsfile: inventory' in config.yaml")
    print("- Verify Genie: pip install genie")
    print("- Test SSH: ssh -i ~/.ssh/id_rsa root@192.168.1.121")
    print("- Check inventory: ansible-inventory -i inventory --list")