# python3 -m exemple.dynamicCommunityExample
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yadygaga"))

import networkx as nx
from yadygaga.dynaGraph import dynamicGraph
from yadygaga.dyCoDeTa import DynaGraphCommuDetection, AnalyzerDynaCommu, visualizer


def main():
    viz = True
    DynaGa = dynamicGraph()
    G1 = nx.Graph()
    G1.add_edges_from(
        [
            ("A", "D"),
            ("A", "E"),
            ("A", "B"),
            ("D", "B"),
            ("D", "E"),
            ("B", "E"),
            ("B", "F"),
            ("B", "C"),
            ("C", "F"),
            ("C", "E"),
            ("E", "F"),
            ("E", "G"),
            ("G", "H"),
            ("G", "J"),
            ("G", "I"),
            ("H", "I"),
            ("I", "J"),
            ("H", "J"),
            ("K", "L"),
            ("K", "M"),
            ("K", "N"),
            ("K", "O"),
            ("L", "M"),
            ("M", "N"),
            ("N", "O"),
            ("O", "L"),
            ("L", "N"),
            ("M", "O"),
            ("K", "C"),
            ("N", "J"),
        ]
    )
    G2 = nx.Graph()
    G2.add_edges_from(
        [
            ("A", "D"),
            ("A", "E"),
            ("A", "B"),
            ("D", "B"),
            ("D", "E"),
            ("B", "E"),
            ("B", "F"),
            ("B", "C"),
            ("C", "F"),
            ("C", "E"),
            ("E", "F"),
            ("E", "G"),
            ("G", "H"),
            ("G", "J"),
            ("G", "I"),
            ("H", "I"),
            ("I", "J"),
            ("H", "J"),
            ("K", "L"),
            ("K", "M"),
            ("K", "N"),
            ("K", "O"),
            ("L", "M"),
            ("M", "N"),
            ("N", "O"),
            ("O", "L"),
            ("L", "N"),
            ("M", "O"),
            ("K", "C"),
            ("N", "J"),
        ]
    )
    G3 = nx.Graph()
    G3.add_edges_from(
        [
            ("A", "D"),
            ("A", "E"),
            ("A", "B"),
            ("D", "B"),
            ("D", "E"),
            ("B", "E"),
            ("B", "F"),
            ("B", "C"),
            ("C", "F"),
            ("C", "E"),
            ("E", "F"),
            ("E", "G"),
            ("G", "H"),
            ("O", "J"),
            ("G", "I"),
            ("H", "I"),
            ("L", "J"),
            ("M", "J"),
            ("K", "L"),
            ("K", "M"),
            ("K", "N"),
            ("K", "O"),
            ("L", "M"),
            ("M", "N"),
            ("N", "O"),
            ("O", "L"),
            ("L", "N"),
            ("M", "O"),
            ("K", "C"),
            ("N", "J"),
        ]
    )
    G4 = nx.Graph()
    G4.add_edges_from(
        [
            ("A", "D"),
            ("A", "E"),
            ("A", "B"),
            ("D", "B"),
            ("D", "E"),
            ("B", "E"),
            ("B", "F"),
            ("B", "C"),
            ("C", "F"),
            ("C", "E"),
            ("E", "F"),
            ("E", "G"),
            ("G", "H"),
            ("G", "J"),
            ("G", "I"),
            ("H", "I"),
            ("I", "J"),
            ("H", "J"),
            ("K", "L"),
            ("K", "M"),
            ("K", "N"),
            ("K", "O"),
            ("L", "M"),
            ("M", "N"),
            ("N", "O"),
            ("O", "L"),
            ("L", "N"),
            ("M", "O"),
            ("K", "C"),
            ("N", "J"),
        ]
    )
    DynaGa.appendGraph(G1)
    DynaGa.appendGraph(G2)
    DynaGa.appendGraph(G3)
    DynaGa.appendGraph(G4)

    print("Dynamic Community Detection Test")
    # Using the SPCDynamicGraph from the previous SPC test
    detector = DynaGraphCommuDetection(DynaGa.DynamicGraph, method="louvain", seed=444)
    communities = detector.detectStatCommunities()
    print("Detected communities for frame 1: ", communities[0])
    comm_mapper = detector.unitCirclePlacement()
    print("Community based node placement for frame 1: ", comm_mapper)
    if viz == True:
        detector.plotCommuMapper()
    detector.HspacePlacement(frame_index=0)
    print("Community positions in H space for frame 1: ", detector.HspaceMapper[0])
    if viz == True:
        detector.plotHspacePlacement(frame_index=0)
    detector.HspacePropagation(threshold=0.5)
    if viz == True:
        detector.plotDynaCommunity()

    # Exemple of usage of AnalyzerDynaCommu
    analyzer = AnalyzerDynaCommu(detector.dynaCommunity)
    dynaCommulifetime = analyzer.commuLifeTime()
    print("Dynamic community lifetime: ", dynaCommulifetime)
    flexibilityScores = analyzer.flexibility()
    print("Flexibility scores: ", flexibilityScores)
    if viz == True:
        vizu = visualizer(DynaGa.DynamicGraph, flexibilityScores)
        vizu.flexibilityVisualization()


if __name__ == "__main__":
    main()
