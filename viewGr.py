import networkx as nx
import matplotlib.pyplot as plt

# Load the GraphML file
G = nx.read_graphml('/Users/PetrAir/examples/cisco_3560_network_map.graphml')

# Visualize
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'), node_color='lightblue', node_size=500, font_size=10)
edge_labels = nx.get_edge_attributes(G, 'local_port')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
plt.title("Network Topology")
plt.show()