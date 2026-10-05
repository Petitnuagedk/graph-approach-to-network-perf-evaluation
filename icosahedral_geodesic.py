"""
Icosahedral Geodesic Polyhedron Graph Generator

This module generates NetworkX graphs representing icosahedral geodesic polyhedra,
which are subdivisions of a regular icosahedron projected onto a sphere.

References:
    - https://en.wikipedia.org/wiki/Geodesic_polyhedron
    - https://en.wikipedia.org/wiki/Geodesic_dome
"""

import networkx as nx
import numpy as np


def create_icosahedral_geodesic_graph(m, n):
    """
    Create a NetworkX graph representing an icosahedral geodesic polyhedron.
    
    A geodesic polyhedron is created by subdividing the faces of a regular icosahedron
    and projecting the resulting vertices onto a sphere. The subdivision is controlled
    by parameters m and n, which define the frequency ν = m + n.
    
    Classification:
    - Class I (Alternate): m ≠ 0, n = 0
    - Class II (Triacon): m = 0, n ≠ 0  
    - Class III: m ≠ 0, n ≠ 0
    
    For frequency ν > 0:
    - Expected vertices: V = 10ν² + 2
    - Expected edges: E = 30ν²
    - Expected faces: F = 20ν²
    
    Parameters
    ----------
    m : int
        First subdivision parameter (non-negative)
    n : int
        Second subdivision parameter (non-negative)
        
    Returns
    -------
    G : NetworkX Graph
        Undirected graph with:
        - Nodes representing vertices of the geodesic polyhedron
        - Edges representing connections between vertices
        - Node attribute 'pos': 3D position on unit sphere (numpy array)
        
    Examples
    --------
    >>> G = create_icosahedral_geodesic_graph(1, 0)  # Frequency 1
    >>> print(G.number_of_nodes(), G.number_of_edges())
    12 30
    
    >>> G = create_icosahedral_geodesic_graph(2, 0)  # Frequency 2
    >>> print(G.number_of_nodes(), G.number_of_edges())
    42 120
    
    >>> G = create_icosahedral_geodesic_graph(2, 1)  # Frequency 3
    >>> print(G.number_of_nodes(), G.number_of_edges())
    92 270
    
    Raises
    ------
    TypeError
        If m or n are not integers
    ValueError
        If m or n are negative
    """
    
    # Validate inputs
    if not isinstance(m, int) or not isinstance(n, int):
        raise TypeError("Parameters m and n must be integers")
    if m < 0 or n < 0:
        raise ValueError("Parameters m and n must be non-negative")
    
    frequency = m + n
    
    # Special case: frequency 0 is just the base icosahedron
    if frequency == 0:
        return _create_base_icosahedron()
    
    # Step 1: Define base icosahedron vertices
    phi = (1 + np.sqrt(5)) / 2  # Golden ratio
    
    base_vertices = np.array([
        [0, 1, phi], [0, 1, -phi], [0, -1, phi], [0, -1, -phi],
        [1, phi, 0], [1, -phi, 0], [-1, phi, 0], [-1, -phi, 0],
        [phi, 0, 1], [phi, 0, -1], [-phi, 0, 1], [-phi, 0, -1]
    ])
    
    # Normalize to unit sphere
    base_vertices = base_vertices / np.linalg.norm(base_vertices, axis=1)[:, np.newaxis]
    
    # Step 2: Define the 20 faces of the icosahedron
    # Vertices are ordered consistently (counter-clockwise when viewed from outside)
    faces = [
        [0, 2, 8], [0, 8, 4], [0, 4, 6], [0, 6, 10], [0, 10, 2],
        [3, 1, 9], [3, 9, 5], [3, 5, 7], [3, 7, 11], [3, 11, 1],
        [2, 5, 8], [8, 5, 9], [9, 4, 8], [4, 9, 1], [1, 6, 4],
        [6, 1, 11], [11, 10, 6], [10, 11, 7], [7, 2, 10], [2, 7, 5]
    ]
    
    # Step 3: Create graph and subdivide faces
    G = nx.Graph()
    vertex_dict = {}
    node_counter = [0]
    
    def get_or_create_node(pos):
        """Get existing node ID or create new one for given position on sphere"""
        pos = pos / np.linalg.norm(pos)  # Project to unit sphere
        key = tuple(np.round(pos, decimals=10))  # Use as hash key
        
        if key not in vertex_dict:
            vertex_dict[key] = node_counter[0]
            G.add_node(node_counter[0], pos=pos)
            node_counter[0] += 1
        
        return vertex_dict[key]
    
    def subdivide_face(v0, v1, v2, freq):
        """
        Subdivide a triangular face using barycentric coordinates.
        
        The triangle is divided into freq² smaller triangles using a regular
        grid pattern. Each vertex is projected onto the unit sphere to create
        the geodesic surface.
        
        The grid is arranged as:
             (0,freq)
                *
               /|\
              / | \
             /  |  \
            /   |   \
           /    |    \
          *-----*-----*
        (0,0)       (freq,0)
        
        Parameters
        ----------
        v0, v1, v2 : ndarray
            The three vertices of the triangle (3D coordinates)
        freq : int
            Subdivision frequency
        """
        # Create grid of points using barycentric coordinates
        points = {}
        
        for i in range(freq + 1):
            for j in range(freq + 1 - i):
                k = freq - i - j
                
                # Barycentric weights (sum to 1)
                w0, w1, w2 = k / freq, i / freq, j / freq
                
                # Linear interpolation on original triangle
                point = w0 * v0 + w1 * v1 + w2 * v2
                
                # Create node (will be projected to sphere)
                node_id = get_or_create_node(point)
                points[(i, j)] = node_id
        
        # Create edges for the triangulated grid
        # We create edges for each small triangle in the subdivision
        # For each position (i,j), we check if we can form triangles
        
        for i in range(freq):
            for j in range(freq - i):
                # Current point
                p00 = points.get((i, j))
                
                # Right neighbor
                p10 = points.get((i + 1, j))
                
                # Upper neighbor
                p01 = points.get((i, j + 1))
                
                # Diagonal neighbor
                p11 = points.get((i + 1, j + 1))
                
                # Triangle pointing up: (i,j), (i+1,j), (i,j+1)
                if p00 is not None and p10 is not None and p01 is not None:
                    G.add_edge(p00, p10)
                    G.add_edge(p10, p01)
                    G.add_edge(p01, p00)
                
                # Triangle pointing down: (i+1,j), (i+1,j+1), (i,j+1)
                # This exists only when not on the edge
                if p10 is not None and p11 is not None and p01 is not None:
                    G.add_edge(p10, p11)
                    G.add_edge(p11, p01)
                    G.add_edge(p01, p10)
    
    # Subdivide all faces
    for face in faces:
        v0, v1, v2 = [base_vertices[idx] for idx in face]
        subdivide_face(v0, v1, v2, frequency)
    
    return G


def _create_base_icosahedron():
    """Create the base icosahedron graph (frequency 0)"""
    G = nx.Graph()
    
    phi = (1 + np.sqrt(5)) / 2
    vertices = np.array([
        [0, 1, phi], [0, 1, -phi], [0, -1, phi], [0, -1, -phi],
        [1, phi, 0], [1, -phi, 0], [-1, phi, 0], [-1, -phi, 0],
        [phi, 0, 1], [phi, 0, -1], [-phi, 0, 1], [-phi, 0, -1]
    ])
    vertices = vertices / np.linalg.norm(vertices, axis=1)[:, np.newaxis]
    
    # Add nodes
    for i, pos in enumerate(vertices):
        G.add_node(i, pos=pos)
    
    # Add edges (each vertex connects to 5 neighbors)
    edges = [
        (0, 2), (0, 4), (0, 6), (0, 8), (0, 10),
        (1, 3), (1, 4), (1, 6), (1, 9), (1, 11),
        (2, 5), (2, 7), (2, 8), (2, 10), (3, 5),
        (3, 7), (3, 9), (3, 11), (4, 6), (4, 8),
        (4, 9), (5, 7), (5, 8), (5, 9), (6, 10),
        (6, 11), (7, 10), (7, 11), (8, 9), (10, 11)
    ]
    
    G.add_edges_from(edges)
    return G


def get_geodesic_stats(G):
    """
    Get statistics about a geodesic polyhedron graph.
    
    Parameters
    ----------
    G : NetworkX Graph
        Geodesic polyhedron graph
        
    Returns
    -------
    dict
        Dictionary with statistics including vertices, edges, faces,
        degree distribution, and Euler characteristic
    """
    stats = {
        'vertices': G.number_of_nodes(),
        'edges': G.number_of_edges(),
    }
    
    # Calculate faces using Euler's formula: V - E + F = 2
    stats['faces'] = 2 - stats['vertices'] + stats['edges']
    
    # Degree distribution
    degrees = dict(G.degree())
    stats['min_degree'] = min(degrees.values())
    stats['max_degree'] = max(degrees.values())
    stats['avg_degree'] = sum(degrees.values()) / len(degrees)
    
    # Euler characteristic (should be 2 for sphere)
    stats['euler_characteristic'] = stats['vertices'] - stats['edges'] + stats['faces']
    
    return stats


if __name__ == "__main__":
    # Test and verify against theoretical formulas
    print("Icosahedral Geodesic Polyhedron Graph Generator")
    print("=" * 70)
    print()
    
    test_cases = [
        (0, 0, "Base Icosahedron"),
        (1, 0, "Class I, freq 1"),
        (2, 0, "Class I, freq 2"),
        (3, 0, "Class I, freq 3"),
        (0, 1, "Class II, freq 1"),
        (0, 2, "Class II, freq 2"),
        (0, 3, "Class II, freq 3"),
        (1, 1, "Class III, freq 2"),
        (2, 1, "Class III, freq 3"),
        (1, 2, "Class III, freq 3"),
    ]
    
    for m, n, description in test_cases:
        G = create_icosahedral_geodesic_graph(m, n)
        freq = m + n
        
        # Theoretical values
        if freq == 0:
            expected_vertices = 12
            expected_edges = 30
            expected_faces = 20
        else:
            expected_vertices = 10 * freq**2 + 2
            expected_edges = 30 * freq**2
            expected_faces = 20 * freq**2
        
        actual_v = G.number_of_nodes()
        actual_e = G.number_of_edges()
        actual_f = 2 - actual_v + actual_e  # Euler's formula
        
        print(f"{description} (m={m}, n={n}):")
        print(f"  Frequency: ν = {freq}")
        print(f"  Vertices: {actual_v:4d} (expected: {expected_vertices:4d}) "
              f"{'✓' if actual_v == expected_vertices else '✗'}")
        print(f"  Edges:    {actual_e:4d} (expected: {expected_edges:4d}) "
              f"{'✓' if actual_e == expected_edges else '✗'}")
        print(f"  Faces:    {actual_f:4d} (expected: {expected_faces:4d}) "
              f"{'✓' if actual_f == expected_faces else '✗'}")
        print()
