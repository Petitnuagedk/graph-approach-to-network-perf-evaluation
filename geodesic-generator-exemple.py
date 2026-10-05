"""
Example usage of the icosahedral geodesic graph generator
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import networkx as nx
import numpy as np
import csv
from icosahedral_geodesic import create_icosahedral_geodesic_graph, get_geodesic_stats


def visualize_geodesic_graph(G, title="Geodesic Polyhedron", figsize=(12, 10),
                             highlight_nodes=None, highlight_color='green', default_color='red'):
    """
    Visualize a geodesic polyhedron graph in 3D.

    Parameters
    ----------
    G : NetworkX Graph
        Geodesic polyhedron graph with 'pos' node attributes
    title : str
        Title for the plot
    figsize : tuple
        Figure size (width, height)
    highlight_nodes : iterable or None
        List/iterable of nodes to highlight. Accepts:
         - node keys exactly as in G (int or str)
         - strings of the form "Node_<index>" which map to the node at that index in list(G.nodes())
         - integers (interpreted as node key if present) or numeric strings
    highlight_color : str
        Color used for highlighted nodes
    default_color : str
        Color used for other nodes
    """
    def _resolve_highlight_keys(G, items):
        if not items:
            return set()
        nodes_list = list(G.nodes())
        resolved = set()
        for it in items:
            # pass-through if exact key exists
            if it in G:
                resolved.add(it)
                continue
            # if it's an int or numeric string and matches a key
            try:
                ik = int(it)
                if ik in G:
                    resolved.add(ik)
                    continue
            except Exception:
                pass
            # support "Node_<index>" -> map to nodes_list[index]
            if isinstance(it, str) and it.startswith("Node_"):
                try:
                    idx = int(it.split("_", 1)[1])
                    if 0 <= idx < len(nodes_list):
                        resolved.add(nodes_list[idx])
                        continue
                except Exception:
                    pass
            # fallback: try to interpret as numeric index into nodes_list
            try:
                idx = int(it)
                if 0 <= idx < len(nodes_list):
                    resolved.add(nodes_list[idx])
            except Exception:
                pass
        return resolved

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')

    # Extract positions
    nodes = list(G.nodes())
    positions = np.array([G.nodes[node]['pos'] for node in nodes])

    # Determine highlighted keys
    highlighted = _resolve_highlight_keys(G, highlight_nodes)

    # Plot edges
    for edge in G.edges():
        pos1 = G.nodes[edge[0]]['pos']
        pos2 = G.nodes[edge[1]]['pos']
        ax.plot([pos1[0], pos2[0]],
                [pos1[1], pos2[1]],
                [pos1[2], pos2[2]],
                'b-', alpha=0.3, linewidth=0.5)

    # Plot nodes with colors according to highlight set
    node_colors = [highlight_color if n in highlighted else default_color for n in nodes]
    scatter = ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2],
                         c=node_colors, s=20, alpha=0.9, depthshade=True)

    # Set equal aspect ratio
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title(title)

    # Set equal scaling
    max_range = 1.1
    ax.set_xlim([-max_range, max_range])
    ax.set_ylim([-max_range, max_range])
    ax.set_zlim([-max_range, max_range])

    # return scatter and nodes list so caller can update colors interactively
    return fig, ax, scatter, nodes


def compare_geodesic_classes(max_freq=3):
    """
    Compare the three classes of geodesic polyhedra.
    """
    print("Comparison of Geodesic Polyhedron Classes")
    print("=" * 80)
    print()
    
    for freq in range(1, max_freq + 1):
        print(f"Frequency ν = {freq}:")
        print("-" * 80)
        
        # Class I (m=freq, n=0)
        G1 = create_icosahedral_geodesic_graph(freq, 0)
        stats1 = get_geodesic_stats(G1)
        
        # Class II (m=0, n=freq)
        G2 = create_icosahedral_geodesic_graph(0, freq)
        stats2 = get_geodesic_stats(G2)
        
        # Class III (if freq >= 2)
        if freq >= 2:
            m = freq // 2
            n = freq - m
            G3 = create_icosahedral_geodesic_graph(m, n)
            stats3 = get_geodesic_stats(G3)
        
        print(f"  Class I   (m={freq}, n=0): V={stats1['vertices']:3d}, "
              f"E={stats1['edges']:3d}, F={stats1['faces']:3d}")
        print(f"  Class II  (m=0, n={freq}): V={stats2['vertices']:3d}, "
              f"E={stats2['edges']:3d}, F={stats2['faces']:3d}")
        
        if freq >= 2:
            print(f"  Class III (m={m}, n={n}): V={stats3['vertices']:3d}, "
                  f"E={stats3['edges']:3d}, F={stats3['faces']:3d}")
        
        print()


def analyze_graph_properties(m, n):
    """
    Analyze various graph properties of a geodesic polyhedron.
    
    Parameters
    ----------
    m, n : int
        Geodesic parameters
    """
    G = create_icosahedral_geodesic_graph(m, n)
    freq = m + n
    
    print(f"\nGraph Analysis for Geodesic Polyhedron (m={m}, n={n}, ν={freq})")
    print("=" * 70)
    
    stats = get_geodesic_stats(G)
    
    print(f"\nBasic Statistics:")
    print(f"  Vertices: {stats['vertices']}")
    print(f"  Edges: {stats['edges']}")
    print(f"  Faces: {stats['faces']}")
    print(f"  Euler characteristic: {stats['euler_characteristic']}")
    
    print(f"\nDegree Statistics:")
    print(f"  Minimum degree: {stats['min_degree']}")
    print(f"  Maximum degree: {stats['max_degree']}")
    print(f"  Average degree: {stats['avg_degree']:.2f}")
    
    # Degree distribution
    degrees = dict(G.degree())
    degree_counts = {}
    for deg in degrees.values():
        degree_counts[deg] = degree_counts.get(deg, 0) + 1
    
    print(f"\nDegree Distribution:")
    for deg in sorted(degree_counts.keys()):
        print(f"  Degree {deg}: {degree_counts[deg]} vertices")
    
    # Connectivity
    print(f"\nConnectivity:")
    print(f"  Is connected: {nx.is_connected(G)}")
    print(f"  Diameter: {nx.diameter(G)}")
    print(f"  Average shortest path: {nx.average_shortest_path_length(G):.2f}")
    print(f"  Radius: {nx.radius(G)}")
    
    # Check planarity (should not be planar for sphere embedding)
    print(f"  Is planar: {nx.check_planarity(G)[0]}")


def create_comparison_figure():
    """
    Create a figure comparing different geodesic frequencies.
    """
    fig = plt.figure(figsize=(18, 6))
    
    examples = [
        (1, 0, "Frequency 1 (Class I)"),
        (2, 0, "Frequency 2 (Class I)"),
        (3, 0, "Frequency 3 (Class I)")
    ]
    
    for idx, (m, n, title) in enumerate(examples):
        G = create_icosahedral_geodesic_graph(m, n)
        ax = fig.add_subplot(1, 3, idx + 1, projection='3d')
        
        positions = np.array([G.nodes[node]['pos'] for node in G.nodes()])
        
        # Plot edges
        for edge in G.edges():
            pos1 = G.nodes[edge[0]]['pos']
            pos2 = G.nodes[edge[1]]['pos']
            ax.plot([pos1[0], pos2[0]], 
                    [pos1[1], pos2[1]], 
                    [pos1[2], pos2[2]], 
                    'b-', alpha=0.3, linewidth=0.5)
        
        # Plot nodes
        ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2], 
                   c='red', s=10, alpha=0.6)
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(f"{title}\nV={G.number_of_nodes()}, E={G.number_of_edges()}")
        
        max_range = 1.1
        ax.set_xlim([-max_range, max_range])
        ax.set_ylim([-max_range, max_range])
        ax.set_zlim([-max_range, max_range])
    
    plt.tight_layout()
    return fig


def save_adjacency_matrix_csv(G, filename):
    """
    Save adjacency matrix of graph G as a CSV with header Node_0,Node_1,...
    Rows contain 0/1 entries corresponding to adjacency.
    """
    nodes = list(G.nodes())
    n = len(nodes)
    # Use NetworkX to get adjacency in node order
    adj = nx.to_numpy_array(G, nodelist=nodes, dtype=int)
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        header = [f"Node_{i}" for i in range(n)]
        writer.writerow(header)
        for row in adj.astype(int):
            writer.writerow(row.tolist())


if __name__ == "__main__":
    # Example 1: Compare geodesic classes
    compare_geodesic_classes(max_freq=4)

    # Example 2: Detailed analysis of a specific geodesic
    analyze_graph_properties(2, 1)

    # Example 3: Create visualizations
    print("\nCreating visualizations...")

    # Single interactive visualization (start with Node_28 and Node_6 highlighted)
    G = create_icosahedral_geodesic_graph(3, 0)
    fig1, ax1, scatter1, nodes = visualize_geodesic_graph(
        G, "Geodesic Polyhedron (interactive)", highlight_nodes=['Node_28', 'Node_70'])

    # helper to resolve user tokens to actual node keys
    def resolve_tokens(tokens, nodes_list):
        if not tokens:
            return set()
        resolved = set()
        for it in tokens:
            it = it.strip()
            if not it:
                continue
            # exact key
            if it in G:
                resolved.add(it); continue
            # Node_<idx>
            if it.startswith("Node_"):
                try:
                    idx = int(it.split("_", 1)[1])
                    if 0 <= idx < len(nodes_list):
                        resolved.add(nodes_list[idx])
                        continue
                except Exception:
                    pass
            # numeric index or key
            try:
                ik = int(it)
                if ik in G:
                    resolved.add(ik); continue
                if 0 <= ik < len(nodes_list):
                    resolved.add(nodes_list[ik]); continue
            except Exception:
                pass
            # fallback: literal
            resolved.add(it)
        return resolved

    plt.ion()
    fig1.show()
    print("Interactive viewer: type comma-separated node tokens to highlight (e.g. Node_28,Node_6 or 28,6).")
    print("Enter empty line to clear highlights. Enter 'q' to close.")
    try:
        while True:
            s = input("highlight> ")
            if s.strip().lower() == 'q':
                break
            tokens = [t for t in s.split(",")] if s.strip() != "" else []
            highlighted = resolve_tokens(tokens, nodes)
            # recompute colors and update scatter
            node_colors = [ 'green' if n in highlighted else 'red' for n in nodes ]
            scatter1.set_facecolor(node_colors)
            scatter1.set_edgecolor(node_colors)
            plt.draw()
            plt.pause(0.05)
    except (KeyboardInterrupt, EOFError):
        pass
    plt.ioff()
    plt.close(fig1)
    print("Interactive viewer closed.")

    # Comparison figure
    fig2 = create_comparison_figure()
    plt.savefig('geodesic_comparison.png', dpi=150, bbox_inches='tight')
    print("  Saved: geodesic_comparison.png")
    
    # Example 4: Export graph for further analysis
    G = create_icosahedral_geodesic_graph(3, 1)
    
    # Save as adjacency list
    nx.write_adjlist(G, 'geodesic_graph.adjlist')
    print("\nExported graph as adjacency list: geodesic_graph.adjlist")
    
    # Save as edge list
    nx.write_edgelist(G, 'geodesic_graph.edgelist')
    print("Exported graph as edge list: geodesic_graph.edgelist")
    
    # Save adjacency matrix as CSV (rows correspond to Node_0..Node_{N-1})
    save_adjacency_matrix_csv(G, 'geodesic_adjacency_matrix.csv')
    print("Exported adjacency matrix CSV: geodesic_adjacency_matrix.csv")
    
    print("\nDone!")
