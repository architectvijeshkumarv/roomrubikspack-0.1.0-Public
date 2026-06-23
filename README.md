# RoomRubiksPack (Client Library)

[![PyPI version](https://badge.fury.io/py/roomrubikspack.svg)](https://pypi.org/project/roomrubikspack/)
[![GitHub repo](https://img.shields.io/badge/GitHub-Repository-blue.svg)](https://github.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public/tree/main)

**Links:**
- **PyPI:** [https://pypi.org/project/roomrubikspack/](https://pypi.org/project/roomrubikspack/)
- **GitHub:** [https://github.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public/tree/main](https://github.com/architectvijeshkumarv/roomrubikspack-0.1.0-Public/tree/main)

RoomRubiksPack is a lightweight Python package for generating architectural floorplan layouts using procedural generation and an Elitist Genetic Algorithm. 

This client library maintains a local, stateful API for creating room models, local graphing/connectivity check, local plotting/visualisation via `matplotlib`, and local CAD exports via `ezdxf`. The computationally heavy layout generation (GA) and auto-dimensioning are offloaded to a RoomRubiks API Server.

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

## Configuring the Server Connection

By default, the client library will look for your live API server running at `https://roomrubikspack-0-1-0-private-942524616275.asia-south1.run.app`. 

You can point to a different server endpoint in two ways:

### 1. In Python Code (Recommended)
Set the URL dynamically via `rr.settings()`:
```python
import roomrubikspack as rr

rr.init()
rr.settings(server_url="https://roomrubikspack-0-1-0-private-942524616275.asia-south1.run.app")
```

### 2. Via Environment Variable
Before running your script, set the `ROOMRUBIKSPACK_SERVER_URL` environment variable:
```bash
# Windows PowerShell
$env:ROOMRUBIKSPACK_SERVER_URL="https://roomrubikspack-0-1-0-private-942524616275.asia-south1.run.app"

# Windows Command Prompt
set ROOMRUBIKSPACK_SERVER_URL=https://roomrubikspack-0-1-0-private-942524616275.asia-south1.run.app

# Linux/macOS
export ROOMRUBIKSPACK_SERVER_URL="https://roomrubikspack-0-1-0-private-942524616275.asia-south1.run.app"
```

---

## Quick Start

Here is a complete example. Make sure your local or remote RoomRubiks server is running before executing this script.

```python
import roomrubikspack as rr

# Initialize session
rr.init()

# Configure the server (defaults to your live Cloud Run URL if omitted)
rr.settings(unit="m", server_url="https://roomrubikspack-0-1-0-private-942524616275.asia-south1.run.app")

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

# Optional: Draw connectivity graph locally
rr.connectivityshow()

# Add constraints to guide layout generation
rr.constraint("position", "bed1", "N")
rr.constraint("area", None, 120)
rr.constraint("perimeter", None, "minimize")

# Generate sizes for rooms missing width/height
rr.dimensiongen()

# Generate layout variations (sent to the server engine)
rr.generatelayout()

# View first variation locally
rr.showlayout(n=1, label=["name", "dim", "area"])

# Export layout to DXF locally
rr.exportlayout(n=1, filepath="output_layout.dxf")

# Blocks execution until plots are closed
rr.wait_for_plots()
```

---

## API Reference

- `rr.init()`: Clears all current session state.
- `rr.settings(unit, server_url)`: Set global measurement units (`'m'` or `'f'`) and configure the solver backend API endpoint.
- `rr.constructiongrid(add, remove, reset)`: View or manipulate the base construction grid sizes locally.
- `rr.room(id, name, w, h, area, startSpace, attachedSpace, ...)`: Register a room.
- `rr.site(points)`: Set an optional site boundary polygon.
- `rr.connectivity(*pairs)`: Define room connections. Planarity check runs instantly on the client.
- `rr.connectivityshow()`: Opens a Matplotlib window showing the adjacency graph.
- `rr.constraint(type, room_id, value)`: Registers a layout constraint.
- `rr.dimensiongen(avar, mar)`: Requests standard room dimensions from the server.
- `rr.generatelayout(lvar, sgap, max_variations)`: Sends session state to the server to run the GA layout engine.
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
