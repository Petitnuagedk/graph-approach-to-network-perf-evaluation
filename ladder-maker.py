import networkx as nx
import matplotlib.pyplot as plt
from typing import Optional, Dict


def plot_graph(
    G: nx.Graph,
    layout: str = "spectral",
    with_labels: bool = True,
    node_size: int = 600,
    node_color: str = "skyblue",
    edge_color: str = "gray",
    figsize=(8, 6),
    save_path: Optional[str] = None,
):
    """
    Draw graph using matplotlib. layout: 'spectral' or any layout accepted by networkx.
    If save_path is given, save PNG to that path instead of (or in addition to) showing.
    Returns the position dict used.
    """
    if layout == "spectral":
        pos = nx.spectral_layout(G)
    elif layout == "kamada_kawai":
        pos = nx.kamada_kawai_layout(G)
    elif layout == "spring":
        pos = nx.spring_layout(G)
    else:
        # fallback: try to use networkx layout by name
        try:
            pos_fn = getattr(nx, f"{layout}_layout")
            pos = pos_fn(G)
        except Exception:
            pos = nx.spring_layout(G)

    plt.figure(figsize=figsize)
    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=node_color)
    nx.draw_networkx_edges(G, pos, edge_color=edge_color)
    if with_labels:
        nx.draw_networkx_labels(G, pos, font_size=10)
    plt.axis("off")
    if save_path:
        plt.tight_layout()
        plt.savefig(save_path, dpi=200)
    else:
        plt.show()
    return pos


def spectral_positions(G: nx.Graph) -> Dict:
    """Return spectral positions (dict) for G (handy for programmatic use)."""
    return nx.spectral_layout(G)


def build_ladder_with_terminals(length):
    if length < 1:
        raise ValueError("length >= 1")
    L = nx.ladder_graph(length)  # 2 x length nodes
    G = nx.Graph()
    # name internal nodes like A1/B1, A2/B2, ...
    for i in range(length):
        left = f"A{i+1}"
        right = f"B{i+1}"
        G.add_node(left); G.add_node(right)
    # add ladder edges (vertical rungs and horizontal steps)
    for i in range(length):
        G.add_edge(f"A{i+1}", f"B{i+1}")             # rung
        if i + 1 < length:
            G.add_edge(f"A{i+1}", f"A{i+2}")        # left rail
            G.add_edge(f"B{i+1}", f"B{i+2}")        # right rail
    # terminals
    G.add_edge("S", "A1"); G.add_edge("S", "B1")
    G.add_edge("R", f"A{length}"); G.add_edge("R", f"B{length}")
    return G

def build_diagonal_ladder_with_terminals(length):
    """
    Build diagonal-only ladder matching edges:
      S-A1, S-B1
      A1-A2, A2-A3, A3-R
      B1-B2, B2-B3, B3-R
      A1-B2, B1-A2, A2-B3, B2-A3
    (no A_i-B_i rungs)
    """
    if length < 1:
        raise ValueError("length >= 1")
    G = nx.Graph()
    # create nodes
    for i in range(length):
        G.add_node(f"A{i+1}")
        G.add_node(f"B{i+1}")

    # connect rails (A and B chains)
    for i in range(1, length):
        G.add_edge(f"A{i}", f"A{i+1}")
        G.add_edge(f"B{i}", f"B{i+1}")

    # connect terminals to ends
    G.add_edge("S", "A1")
    G.add_edge("S", "B1")
    G.add_edge("R", f"A{length}")
    G.add_edge("R", f"B{length}")

    # add diagonal cross links between successive levels
    for i in range(1, length):
        G.add_edge(f"A{i}", f"B{i+1}")
        G.add_edge(f"B{i}", f"A{i+1}")

    return G

def build_two_lines_with_terminals(length):
    """
    Build two independent path (line) graphs of given length and attach terminals:
      left chain:  A1 - A2 - ... - An
      right chain: B1 - B2 - ... - Bn
    Terminals:
      S connected to A1 and B1
      R connected to An and Bn
    """
    if length < 1:
        raise ValueError("length >= 1")
    G = nx.Graph()
    # create nodes
    for i in range(1, length + 1):
        G.add_node(f"A{i}")
        G.add_node(f"B{i}")
    # connect chains
    for i in range(1, length):
        G.add_edge(f"A{i}", f"A{i+1}")
        G.add_edge(f"B{i}", f"B{i+1}")
    # terminals
    G.add_edge("S", "A1")
    G.add_edge("S", "B1")
    G.add_edge("R", f"A{length}")
    G.add_edge("R", f"B{length}")
    return G

def build_line_with_terminals(length):
    """
    Build a single path (line) of given length and attach terminals:
      A1 - A2 - ... - An
    Terminals:
      S connected to A1
      R connected to An
    """
    if length < 1:
        raise ValueError("length >= 1")
    G = nx.Graph()
    # create nodes A1..An
    for i in range(1, length + 1):
        G.add_node(f"A{i}")
    # connect path
    for i in range(1, length):
        G.add_edge(f"A{i}", f"A{i+1}")
    # terminals
    G.add_edge("S", "A1")
    G.add_edge("R", f"A{length}")
    return G


G = build_ladder_with_terminals(7)
print(nx.info(G))
if __name__ == "__main__":
    # demo: build and plot the diagonal ladder matching requested edges
    G_diag = build_diagonal_ladder_with_terminals(7)
    print(nx.info(G_diag))
    plot_graph(G_diag, layout="kamada_kawai", with_labels=True, figsize=(6, 5))
    plot_graph(G_diag, layout="spring", with_labels=True, figsize=(6, 5), save_path="J2/viz test/diagonal_spring.png")
    # demo: also plot the two-lines topology
    G_two = build_two_lines_with_terminals(7)
    print(nx.info(G_two))
    plot_graph(G_two, layout="kamada_kawai", with_labels=True, figsize=(6, 5), save_path="J2/viz test/two_lines_kamada.png")
    plot_graph(G_two, layout="spring", with_labels=True, figsize=(6, 5), save_path="J2/viz test/two_lines_spring.png")
    # demo: build and plot the single line topology
    G_line = build_line_with_terminals(7)
    print(nx.info(G_line))
    plot_graph(G_line, layout="kamada_kawai", with_labels=True, figsize=(6, 5), save_path="J2/viz test/line_kamada.png")
    plot_graph(G_line, layout="spring", with_labels=True, figsize=(6, 5), save_path="J2/viz test/line_spring.png")