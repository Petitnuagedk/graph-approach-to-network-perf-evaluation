import networkx as nx


class PropertiesChecker:
    """
    PropertiesChecker class to validate properties of graphs or frames.
    """

    def __init__(self):
        pass

    def path_lifetime(graphs, source, destination, fps=1):
        """
        Compute uptime information for a path between source and destination across a list of graphs.

        :param graphs: list of networkx.Graph objects (frames).
        :param source: source node.
        :param destination: destination node.
        :param fps: frames per second (default 1). Used to convert frames to seconds.
        :return: dict with frames_with_path, total_frames, uptime_ratio, uptime_seconds.
        """
        if not graphs:
            raise ValueError("graphs list is empty")

        total_frames = len(graphs)
        frames_with_path = 0
        for g in graphs:
            try:
                if nx.has_path(g, source, destination):
                    frames_with_path += 1
            except nx.NetworkXError:
                # node missing in this frame -> no path
                continue

        uptime_ratio = frames_with_path / total_frames
        uptime_seconds = frames_with_path / fps if fps > 0 else None

        return {
            "frames_with_path": frames_with_path,
            "total_frames": total_frames,
            "uptime_ratio": uptime_ratio,
            "uptime_seconds": uptime_seconds,
        }

    def path_stability(graphs, source, destination):
        """
        Compute stability ratio of a given pair (edge) relative to existence of any path
        between source and destination.

        The ratio is: (frames where pair edge is present) / (frames where any path between source and destination exists).
        If no path ever exists, returns None for the ratio.

        :param graphs: list of networkx.Graph objects (frames).
        :param source: source node (used if pair not provided).
        :param destination: destination node (used if pair not provided).
        :return: dict with frames_pair_up, frames_path_exists, stability_ratio (or None).
        """
        if not graphs:
            raise ValueError("graphs list is empty")

        frames_path_exists = 0
        state = 0  # 1 -> up, 0 -> down
        stateChange = 0

        for g in graphs:
            # count if any path exists between source and destination in this frame
            try:
                if nx.has_path(g, source, destination):
                    frames_path_exists += 1
                    if state == 1:
                        pass
                    elif state == 0:
                        stateChange += 1  # we only count upfront transitions
                        state = 1
                else:
                    if state == 0:
                        pass
                    elif state == 1:
                        state = 0

            except nx.NetworkXError:
                # missing nodes -> no path
                pass

        stability_ratio = None
        possible_changes = len(graphs) / 2
        if frames_path_exists > 0:
            # print(stateChange)
            # print(len(graphs))
            stability_ratio = 1 - (stateChange / possible_changes)

        return {
            "frames_path_exists": frames_path_exists,
            "Number_of_state_changes": stateChange,
            "Number_of_possible_changes": possible_changes,
            "stability_ratio": stability_ratio,
        }

    def path_length(graphs, source, destination):
        """
        Measure shortest path length between source and destination for each frame.

        :param graphs: list of networkx.Graph objects (frames).
        :param source: source node.
        :param destination: destination node.
        :return: dict with:
            - lengths: list where each element is shortest path length (int) or None if no path in that frame
            - frames_with_path: number of frames that have a path
            - total_frames: total number of frames
            - min, max, mean, median (statistics over frames that have a path) or None if no paths
        """
        import statistics

        if not graphs:
            raise ValueError("graphs list is empty")

        lengths = []
        for g in graphs:
            try:
                length = nx.shortest_path_length(g, source, destination)
                lengths.append(int(length))
            except (nx.NetworkXNoPath, nx.NodeNotFound, nx.NetworkXError):
                lengths.append(None)

        present = [l for l in lengths if l is not None]
        stats = {"min": None, "max": None, "mean": None, "median": None}
        if present:
            stats["min"] = min(present)
            stats["max"] = max(present)
            stats["mean"] = statistics.mean(present)
            stats["median"] = statistics.median(present)

        return {
            "lengths": lengths,
            "frames_with_path": len(present),
            "total_frames": len(graphs),
            **stats,
        }

    # def is_connected(self):
    #     """
    #     Check if the graph is connected.

    #     :return: True if the graph is connected, False otherwise.
    #     """
    #     return nx.is_connected(self.graph)

    # def has_cycle(self):
    #     """
    #     Check if the graph contains a cycle.

    #     :return: True if the graph has a cycle, False otherwise.
    #     """
    #     return nx.is_cyclic(self.graph)

    # def validate_node_existence(self, node):
    #     """
    #     Validate if a node exists in the graph.

    #     :param node: The node to check.
    #     :return: True if the node exists, False otherwise.
    #     """
    #     return node in self.graph.nodes()

    # def validate_edge_existence(self, u, v):
    #     """
    #     Validate if an edge exists between two nodes in the graph.

    #     :param u: The first node.
    #     :param v: The second node.
    #     :return: True if the edge exists, False otherwise.
    #     """
    #     return self.graph.has_edge(u, v)

    # def validate_path(self, source, destination):
    #     """
    #     Validate if there is a path between two nodes.

    #     :param source: The source node.
    #     :param destination: The destination node.
    #     :return: True if a path exists, False otherwise.
    #     """
    #     return nx.has_path(self.graph, source, destination)

    # def fullCheck(self, source, destination):
    #     """
    #     Perform a full check of the graph properties.

    #     :param source: The source node for path validation.
    #     :param destination: The destination node for path validation.
    #     :return: A dictionary with the results of all checks.
    #     """
    #     return {
    #         "is_connected": self.is_connected(),
    #         "has_cycle": self.has_cycle(),
    #         "source_exists": self.validate_node_existence(source),
    #         "destination_exists": self.validate_node_existence(destination),
    #         "path_exists": self.validate_path(source, destination)
    #     }
