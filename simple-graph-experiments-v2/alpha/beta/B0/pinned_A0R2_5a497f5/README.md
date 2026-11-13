# YaDyGaGa

YaDyGaGa is a small toolkit to generate, assemble and visualize dynamic graphs (sequences of networkx Graph objects).
It is aimed at experimentation with path uptime, stability and multi-pair scenarios where each frame is a sampled subgraph.

## Requirements
- Python 3.8+
- numpy
- networkx
- matplotlib

Install:
```
pip install -r requirements.txt
```
(ensure a GUI backend for matplotlib when using animation, or save the animation to file)


## Creating a dynamic graph

You can create a dynamic graph (a list of networkx.Graph frames) in two ways: with the repository generators (if you want block/timeline semantics) or quickly by sampling a base graph.

There are complete example in the src/exampleSpcMpc.py file.

## Contributing
- Follow existing module structure and add unit tests for new behavior.
- Keep augmentation deterministic with seeds where reproducibility is needed.

## License
GPL-2.0 (see LICENSE file).

## Contact
Open issues or PRs on the repository for bugs or feature requests.
