from pysnmp.hlapi import SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, getCmd, nextCmd
import networkx as nx
import matplotlib.pyplot as plt
from ipaddress import ip_network

def snmp_get(target: str, community: str, oid: str):
    """Perform SNMP GET using PySNMP 7.1.22."""
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((target, 161), timeout=2, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        error_indication, error_status, error_index, var_binds = next(iterator)
        if error_indication:
            print(f"SNMP error for {target}: {error_indication}")
            return None
        if error_status:
            print(f"SNMP error status for {target}: {error_status.prettyPrint()}")
            return None
        return var_binds[0][1].prettyPrint()
    except Exception as e:
        print(f"SNMP GET failed for {target}: {e}")
        return None

def snmp_walk(target: str, community: str, oid: str):
    """Perform SNMP WALK to retrieve multiple values (e.g., CDP neighbors)."""
    neighbors = []
    try:
        iterator = nextCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((target, 161), timeout=2, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False
        )
        for error_indication, error_status, error_index, var_binds in iterator:
            if error_indication:
                print(f"SNMP walk error for {target}: {error_indication}")
                break
            if error_status:
                print(f"SNMP walk error status for {target}: {error_status.prettyPrint()}")
                break
            for var_bind in var_binds:
                neighbors.append(var_bind[1].prettyPrint())
        return neighbors
    except Exception as e:
        print(f"SNMP walk failed for {target}: {e}")
        return []

def discover_neighbors(ip: str, community: str):
    """Discover CDP neighbors using SNMP (CDP MIB)."""
    cdp_device_id_oid = '1.3.6.1.4.1.9.9.23.1.2.1.1.6'  # cdpCacheDeviceId
    neighbors = snmp_walk(ip, community, cdp_device_id_oid)
    return neighbors

def build_topology(seed_ip: str, community: str, subnet: str, max_depth: int = 5):
    """Build network topology starting from seed_ip."""
    G = nx.Graph()
    to_scan = [(seed_ip, 0)]  # (ip, depth)
    scanned = set()

    while to_scan:
        current, depth = to_scan.pop(0)
        if current in scanned or depth > max_depth:
            continue
        scanned.add(current)

        # Get hostname via sysName OID
        hostname = snmp_get(current, community, '1.3.6.1.2.1.1.5.0') or current
        G.add_node(current, label=hostname)

        # Discover neighbors via CDP
        neighbors = discover_neighbors(current, community)
        for neigh in neighbors:
            G.add_edge(current, neigh)
            if neigh not in scanned:
                to_scan.append((neigh, depth + 1))  # Placeholder: Needs IP resolution

    return G

# Configuration for Cisco C3560
community = 'philips-pscn'  # Replace with your SNMP community string
seed_ip = '192.168.1.121'  # Your Cisco C3560
subnet = '192.168.1.0/24'  # Subnet for context (not fully used here)

graph = build_topology(seed_ip, community, subnet)

# Visualize
pos = nx.spring_layout(graph)
nx.draw(graph, pos, with_labels=True, labels=nx.get_node_attributes(graph, 'label'))
plt.show()

# Export to GraphML
nx.write_graphml(graph, 'cisco_3560_network_map.graphml')