"""
This file initializes the yadygaga package and re-exports the main classes
and helpers for convenient imports like `from yadygaga import FrameGenerator`.
"""

# explicit relative imports (match actual module filenames in src/)
from .frameGenerator import FrameGenerator
from .propertiesChecker import PropertiesChecker
from .timelineBlockGenerator import SPCTimelineBlockGenerator, MPCTimelineBlockGenerator
from .dynaGraph import dynamicGraph, SPCDynamicGraph, MPCDynamicGraph
from .visualizer import Visualizer
from .sourceGraphAugmenter import SourceGraphAugmenter
from .dyCoDeTa import (
    DynaGraphCommuDetection,
    AnalyzerDynaCommu,
    visualizer as dyco_visualizer,
)

# Public API
__all__ = [
    "FrameGenerator",
    "PropertiesChecker",
    "SPCTimelineBlockGenerator",
    "MPCTimelineBlockGenerator",
    "dynamicGraph",
    "SPCDynamicGraph",
    "MPCDynamicGraph",
    "Visualizer",
    "SourceGraphAugmenter",
    "DynaGraphCommuDetection",
    "AnalyzerDynaCommu",
    "dyco_visualizer",
]
