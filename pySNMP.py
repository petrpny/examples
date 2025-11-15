from napalm import get_network_driver
import networkx as nx
import matplotlib.pyplot as plt
import re
from ipaddress import ip_network

def get_cdp_neighbor_details(device):
    """Fetch neighbor details (hostname, IP, ports) from 'show cdp neighbors detail'."""
    try:
        cdp_detail = device.cli(['show cdp neighbors detail'])['show cdp neighbors detail']
        neighbors = []
        current_neigh = {}
        ip_pattern = re.compile(r'IP Address: (\S+)')
        device_pattern = re.compile(r'Device ID: (\S+)')
        interface_pattern = re.compile(r'Interface: (\S+),')
        port_pattern = re.compile(r'Port ID \(outgoing port\): (\S+)')
        
        for line in cdp_detail.splitlines():
            if device_pattern.match(line):
                if current_neigh:
                    neighbors.append(current_neigh)
                current_neigh = {'hostname': device_pattern.match(line).group(1)}
            elif ip_pattern.match(line):
                current_neigh['ip'] = ip_pattern.match(line).group(1)
            elif interface_pattern.match(line):
                current_neigh['local_port'] = interface_pattern.match(line).group(1).replace(',', '')
            elif port_pattern.match(line):
                current_neigh['neighbor_port'] = port_pattern.match(line).group(1)
        if current_neigh:
            neighbors.append(current_neigh)
        print(f"Neighbor details: {neighbors}")
        return neighbors
    except Exception as e:
        print(f"Failed to get CDP neighbor details: {e}")
        return []

def build_cisco_topology(seed_ips: list, username: str, password: str, subnet: str = None, max_depth: int = 5):
    """Build network topology starting from seed_ips or subnet using NAPALM."""
    G = nx.Graph()
    to_scan = [(ip, 0) for ip in seed_ips]
    scanned = set()

    if subnet:
        try:
            network = ip_network(subnet, strict=False)
            to_scan.extend([(str(ip), 0) for ip in network.hosts() if str(ip) not in seed_ips])
            print(f"Scanning subnet {subnet}: {len(to_scan)} IPs")
        except ValueError as e:
            print(f"Invalid subnet {subnet}: {e}")

    driver = get_network_driver('ios')
    while to_scan:
        current, depth = to_scan.pop(0)
        if current in scanned or depth > max_depth:
            continue
        scanned.add(current)
        print(f"Scanning {current} (depth {depth})")

        try:
            device = driver(hostname=current, username=username, password=password)
            device.open()
            facts = device.get_facts()
            neighbors = get_cdp_neighbor_details(device)
            device.close()

            hostname = facts.get('hostname', current)
            G.add_node(current, label=hostname)
            print(f"Added node: {hostname} ({current})")

            for neigh in neighbors:
                neigh_hostname = neigh.get('hostname', current)
                neigh_ip = neigh.get('ip', neigh_hostname)
                local_port = neigh.get('local_port', 'unknown')
                neighbor_port = neigh.get('neighbor_port', 'unknown')
                G.add_edge(current, neigh_ip, local_port=local_port, neighbor_port=neighbor_port)
                print(f"Added edge: {current} -> {neigh_ip} ({local_port} -> {neighbor_port})")
                if neigh_ip not in scanned and depth + 1 <= max_depth:
                    to_scan.append((neigh_ip, depth + 1))
        except Exception as e:
            print(f"Failed for {current}: {e}")

    print("Final nodes:", G.nodes(data=True))
    print("Final edges:", G.edges(data=True))
    return G

# Configuration for Cisco C3560
username = 'root'  # Replace with your SSH username
password = 'PhilipsR00t!'  # Replace with your SSH password
seed_ips = ['172.31.200.2', '172.31.200.3']  # List of starting IPs
subnet =  None # Subnet to scan (set to None if using seed_ips only)

graph = build_cisco_topology(seed_ips, username, password, subnet=subnet)
pos = nx.spring_layout(graph)
nx.draw(graph, pos, with_labels=True, labels=nx.get_node_attributes(graph, 'label'), node_color='lightblue', node_size=500)
edge_labels = {(u, v): f"{d['local_port']} -> {d['neighbor_port']}" for u, v, d in graph.edges(data=True)}
nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
plt.title("Network Topology")
plt.show()
nx.write_graphml(graph, 'cisco_3560_network_map.graphml')
print("Topology map saved as 'cisco_3560_network_map.graphml'")