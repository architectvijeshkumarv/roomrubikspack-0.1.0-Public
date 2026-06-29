# RoomRubiksPack (Client Library)

[![PyPI version](https://badge.fury.io/py/roomrubikspack.svg)](https://pypi.org/project/roomrubikspack/)
[![GitHub repo](https://img.shields.io/badge/GitHub-Repository-blue.svg)](https://github.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public)

**Links:**
- **PyPI:** [https://pypi.org/project/roomrubikspack/](https://pypi.org/project/roomrubikspack/)
- **GitHub:** [https://github.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public](https://github.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public)

**RoomRubiksPack** is a powerful procedural architectural floorplan layout generator package. It optimizes room placement, wall snapping, checks for non-overlapping areas, and inherently supports **Vastu compliance** while respecting predefined connectivity and topological constraints.

This unified version is 100% offline and runs its Elitist Genetic Algorithm entirely on your local machine—no server setup required!

---

## Installation

### Option 1: Install from PyPI
Once published, install the package via:
```bash
pip install roomrubikspack
```

### Option 2: Install from GitHub
```bash
pip install git+https://github.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public.git
```

### Option 3: Local Installation (After Downloading)
Navigate to the directory containing `pyproject.toml` and run:
```bash
pip install .
```
For local developers who want to modify the source code, run in editable mode:
```bash
pip install -e .
```

---

## Quick Start

### 1. Initialization and Settings

```python
import roomrubikspack as rr

# Initialize a new session/project
rr.init()

# Set global preferences (unit: 'm' or 'ft')
rr.settings(unit="m")

# Define Rooms
rr.room("living",   "Living Room",  area=20.0, startSpace=True)
rr.room("kitchen",  "Kitchen",      w=3.0, h=3.0)
rr.room("bed1",     "Master Bed",   area=16.0)
rr.room("bath1",    "Attached Bath", area=4.0, attachedSpace=True)

# Define site boundary
rr.site([{"x": 0, "y": 0}, {"x": 20, "y": 0}, {"x": 20, "y": 20}, {"x": 0, "y": 20}])

# Define connectivity
rr.connectivity(
    ("living", "kitchen"),
    ("living", "bed1"),
    ("bed1",   "bath1")
)

# Enable Vastu compliance (inherently supported)
rr.vastu(True)

# Optional: Draw connectivity graph locally
rr.connectivityshow()

# Add constraints to guide layout generation
rr.constraint("position", "bed1", "N")
rr.constraint("area", None, 120)
rr.constraint("perimeter", None, "minimize")

# Generate sizes for rooms missing width/height
rr.dimensiongen()

# Generate baseline layout variations (sent to the server engine)
rr.generatelayout()

# View first variation locally
rr.showlayout(n=1, label=["name", "dim", "area", "vastu"])

# DEEP REFINEMENT: Tell the GA to deeply optimize the topological shape of Rank 1
# This extracts the shape of Rank 1 and strictly limits a 45-second deep GA search to that topology!
rr.generatelayout(selv=1)

# View the highly-optimized, mathematically clamped variation
rr.showlayout(n=1, label=["name", "dim", "area", "vastu"])

# Export layout to DXF locally
rr.exportlayout(n=1, filepath="output_layout.dxf")

# Blocks execution until plots are closed
rr.wait_for_plots()
```

### Example Visualizations

When you run the script above, you can use the built-in visualisation functions to plot the network graph and the generated floorplan layout using Matplotlib.

**1. Connectivity Network Diagram** (`rr.connectivityshow()`)
![Network Diagram](https://raw.githubusercontent.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public/main/docs/images/1_network_diagram.png)

**2. Layout with Position Constraint (Vastu Off)**
![Position Constraint](https://raw.githubusercontent.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public/main/docs/images/2_position_constraint_result.png)

**3. Layout with Vastu Compliance Engine (No hard constraints needed)**
![Vastu Layout](https://raw.githubusercontent.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public/main/docs/images/3_vastu_result.png)

**4. Generated Layout with Overlaid Connectivity Network** (`shownetwork=True`)
![Layout with Network](https://raw.githubusercontent.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public/main/docs/images/4_layout_with_network.png)

---

## API Reference

- `rr.init()`: Clears all current session state.
- `rr.settings(unit, server_url)`: Set global measurement units (`'m'` or `'f'`) and configure the solver backend API endpoint.
- `rr.constructiongrid(add, remove, reset)`: View or manipulate the base construction grid sizes locally.
- `rr.room(id, name, w, h, area, startSpace, attachedSpace, ...)`: Register a room.
- `rr.site(points)`: Set an optional site boundary polygon.
- `rr.vastu(keep: bool)`: Enable or disable Vastu Shastra rules during generation.
- `rr.connectivity(*pairs)`: Define room connections. Planarity check runs instantly on the client.
- `rr.connectivityshow()`: Opens a Matplotlib window showing the adjacency graph.
- `rr.constraint(type, room_id, value)`: Registers a layout constraint.
- `rr.dimensiongen(avar, mar)`: Requests standard room dimensions from the server.
- `rr.generatelayout(lvar, sgap, max_variations, selv)`: Sends session state to the server to run the GA layout engine. Pass `selv=N` to perform a deep refinement search on the topological shape of the N-th variation.
- `rr.showlayout(n, label)`: Plots the `n`-th generated variation using Matplotlib.
- `rr.exportlayout(n, filepath)`: Saves the `n`-th layout to JSON or DXF.
- `rr.wait_for_plots()`: Helper to keep visual plots open.

---

## Citation

If you use RoomRubiks in your academic or professional work, please cite the following paper:

**APA:**
Valiyappurakkal, V. K. (2026). RoomRubiks: An Application for Floor Layout Generation Using a Nonfragmented Rectangular Approach. *Journal of Architectural Engineering*, 32(3). https://doi.org/10.1061/JAEIED.AEENG-2207

**BibTeX:**
```bibtex
@article{Valiyappurakkal2026RoomRubiks,
  author  = {Valiyappurakkal, Vijesh Kumar},
  title   = {RoomRubiks: An Application for Floor Layout Generation Using a Nonfragmented Rectangular Approach},
  journal = {Journal of Architectural Engineering},
  year    = {2026},
  volume  = {32},
  number  = {3},
  doi     = {10.1061/JAEIED.AEENG-2207},
  url     = {https://doi.org/10.1061/JAEIED.AEENG-2207}
}
```

## Support and Discussions

For any questions, bug reports, feature requests, or general discussions regarding RoomRubiks, please visit our [GitHub Discussions page](https://github.com/Vijesh-Kumar-V/roomrubikspack/discussions). We prefer managing all support requests publicly via GitHub rather than email to help the community build a shared knowledge base.
