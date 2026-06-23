from typing import List, Dict, Tuple, Optional, Any
import json
import dataclasses
import requests
import os

from .types import Room, Connection, Site
from .utils.graph_utils import check_planarity
from .utils.constraints import add_constraint, clear_constraints

# Session state kept on the client side
_rooms: List[Room] = []
_connections: List[Connection] = []
_site: Optional[Site] = None
_layout_variations: List[List[Room]] = []
_DEFAULT_GRID_SIZES: List[float] = [1.2, 1.5, 1.8, 2.1, 2.4, 3.0, 4.5, 6.0, 7.5, 9.0]
_base_grid_sizes: List[float] = _DEFAULT_GRID_SIZES.copy()
_settings: Dict[str, str] = {"unit": "m"}

# Configurable server URL (falls back to live Cloud Run or environment variable)
_server_url: str = os.getenv("ROOMRUBIKSPACK_SERVER_URL", "https://roomrubikspack-0-1-0-private-942524616275.asia-south1.run.app").rstrip('/')


def deserialize_room(r: Dict[str, Any]) -> Room:
    valid_fields = {f.name for f in dataclasses.fields(Room)}
    filtered_data = {k: v for k, v in r.items() if k in valid_fields}
    return Room(**filtered_data)


def init():
    """Initializes a new session/project (clears any existing state)."""
    global _rooms, _connections, _site, _layout_variations, _base_grid_sizes
    _rooms = []
    _connections = []
    _site = None
    _layout_variations = []
    _base_grid_sizes = _DEFAULT_GRID_SIZES.copy()
    clear_constraints()
    print("RoomRubiks session initialized successfully.")


def room(id: str, name: str = "", **kwargs):
    """Adds a room to the session (or updates if ID exists) and prints a success message."""
    global _rooms
    new_room = Room(id=id, name=name, **kwargs)
    
    details = f"Area: {new_room.area} " if new_room.area else f"Size: {new_room.w}x{new_room.h} "
    start_space_msg = " (Start Space)" if new_room.startSpace else ""
    
    # Replace if exists
    for i, existing in enumerate(_rooms):
        if existing.id == id:
            _rooms[i] = new_room
            print(f"Updated existing room: {new_room.name} ({new_room.id}) - {details}{start_space_msg}")
            return new_room
            
    _rooms.append(new_room)
    print(f"Added room successfully: {new_room.name} ({new_room.id}) - {details}{start_space_msg}")
    return new_room


def connectivity(*conn_pairs: Tuple[str, str]):
    """Registers the connections, runs a planarity check, prints a message."""
    global _connections, _rooms
    
    for pair in conn_pairs:
        exists = any((c.roomA == pair[0] and c.roomB == pair[1]) or (c.roomA == pair[1] and c.roomB == pair[0]) for c in _connections)
        if not exists:
            _connections.append(Connection(roomA=pair[0], roomB=pair[1]))
        
    start_spaces = [r for r in _rooms if r.startSpace]
    
    print(f"Added {len(conn_pairs)} connections.")
    
    if len(start_spaces) != 1:
        print(f"WARNING: There must be exactly one start space. Found {len(start_spaces)}.")
    else:
        print(f"Start space verified: {start_spaces[0].name}")
        
    room_ids = [r.id for r in _rooms]
    is_planar = check_planarity(room_ids, _connections)
    if is_planar:
        print("Planarity check passed: The connectivity graph satisfies Euler's formula.")
    else:
        print("WARNING: The provided connectivity graph is non-planar.")


def connectivityshow():
    """Shows a matplotlib network diagram of the registered connectivity."""
    global _connections, _rooms
    if not _rooms or not _connections:
        print("No rooms or connections registered to show.")
        return

    try:
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        print("Please install matplotlib and networkx to use connectivityshow(): pip install matplotlib networkx")
        return

    G = nx.Graph()
    
    for r in _rooms:
        G.add_node(r.id, label=r.name or r.id, is_start=getattr(r, 'startSpace', False))
        
    for c in _connections:
        G.add_edge(c.roomA, c.roomB)

    pos = nx.spring_layout(G, seed=42)
    labels = nx.get_node_attributes(G, 'label')
    colors = ['lightgreen' if nx.get_node_attributes(G, 'is_start').get(n) else 'lightblue' for n in G.nodes()]

    plt.figure(figsize=(8, 6))
    nx.draw(G, pos, labels=labels, node_color=colors, with_labels=True, node_size=2000, font_size=10, font_weight="bold", edge_color="gray")
    plt.title("Connectivity Network Diagram")
    plt.show(block=False)


def site(points: List[Dict[str, float]]):
    """Defines the optional site boundary."""
    global _site
    _site = Site(points=points)
    print("Site boundary added successfully.")


def constraint(constraint_type: str, room_id: Optional[str] = None, value: Any = None):
    """Adds a constraint (e.g. position, area, perimeter) for the layout generator."""
    add_constraint(constraint_type, room_id, value)
    print(f"Added constraint: {constraint_type} for room {room_id} with value {value}")


def settings(unit: Optional[str] = None, server_url: Optional[str] = None):
    """Sets global project settings and server endpoint."""
    global _settings, _server_url
    if unit is not None:
        unit = unit.lower()
        if unit not in ['m', 'f']:
            print("Warning: Unsupported unit. Use 'm' for meters or 'f' for feet.")
        else:
            _settings["unit"] = unit
            print(f"Settings updated: unit set to '{unit}'")
            
    if server_url is not None:
        _server_url = server_url.rstrip('/')
        print(f"Settings updated: server URL set to '{_server_url}'")


def constructiongrid(add: Optional[float] = None, remove: Optional[float] = None, reset: bool = False):
    """Shows or modifies the base construction grid sizes used by dimensiongen."""
    global _base_grid_sizes, _DEFAULT_GRID_SIZES
    
    if reset:
        _base_grid_sizes = _DEFAULT_GRID_SIZES.copy()
        print("Construction grid reset to defaults.")
        return _base_grid_sizes
        
    if add is not None:
        if add not in _base_grid_sizes:
            _base_grid_sizes.append(float(add))
            _base_grid_sizes.sort()
            print(f"Added {add} to construction grid.")
        else:
            print(f"{add} is already in the construction grid.")
    if remove is not None:
        if remove in _base_grid_sizes:
            _base_grid_sizes.remove(float(remove))
            print(f"Removed {remove} from construction grid.")
        else:
            print(f"{remove} is not in the construction grid.")
            
    print(f"Current base construction grid: {_base_grid_sizes}")
    return _base_grid_sizes


def dimensiongen(avar: float = 0.10, mar: float = 1.5):
    """Calculates optimal dimensions for rooms missing them using the server."""
    global _rooms, _base_grid_sizes, _server_url
    
    payload = {
        "rooms": [dataclasses.asdict(r) for r in _rooms],
        "base_grid_sizes": _base_grid_sizes,
        "area_variation": avar,
        "max_aspect_ratio": mar
    }
    
    print(f"Requesting dimensions from server at {_server_url}...")
    try:
        response = requests.post(f"{_server_url}/dimensiongen", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error connecting to RoomRubiks server: {e}")
        print("Please check if the server is running and configured correctly.")
        return {}
        
    # Reconstruct rooms and update _rooms
    updated_rooms = []
    for rm_dict in data["rooms"]:
        updated_rooms.append(deserialize_room(rm_dict))
    _rooms = updated_rooms
    
    saved_dimensions = data["saved_dimensions"]
    print(f"Generated dimensions for {len(saved_dimensions)} rooms.")
    print(f"Dimensions details: {saved_dimensions}")
    return saved_dimensions


def generatelayout(lvar: float = 0.5, sgap: float = 1.0, max_variations: int = 10, liked_layouts: Optional[List[Any]] = None):
    """Generates the architectural layouts using the server-side Elitist Genetic Algorithm."""
    global _rooms, _connections, _site, _settings, _layout_variations, _server_url
    print(f"Generating layout on server ({_server_url}) with location_variation={lvar}, allowed_space_gap={sgap}...")
    
    from .utils.constraints import _global_constraints
    
    payload = {
        "rooms": [dataclasses.asdict(r) for r in _rooms],
        "connections": [dataclasses.asdict(c) for c in _connections],
        "constraints": _global_constraints,
        "site": dataclasses.asdict(_site) if _site is not None else None,
        "settings": _settings,
        "location_variation": lvar,
        "allowed_space_gap": sgap,
        "max_variations": max_variations
    }
    
    try:
        response = requests.post(f"{_server_url}/generatelayout", json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error connecting to RoomRubiks server: {e}")
        print("Please check if the server is running and configured correctly.")
        return []
        
    variations = []
    for var_dict in data["variations"]:
        var_rooms = [deserialize_room(rm_dict) for rm_dict in var_dict["layout"]]
        variations.append({"layout": var_rooms, "score": var_dict["score"]})
        
    _layout_variations = variations
    if not variations:
        print("Failed to generate layouts.")
    else:
        print(f"Successfully generated {len(variations)} unique variations (ranked best to worst).")
        for i, var in enumerate(variations):
            var_rooms = var["layout"]
            total_area = sum(round(r.w * r.h, 1) if r.w and r.h else 0.0 for r in var_rooms)
            print(f"Rank {i+1} Variation - Score: {round(var['score'], 1)} - Total Area: {round(total_area, 1)} m²")
        
    # Print the server's status/fitting report
    status_report = data.get("status_report", "")
    if status_report:
        print(f"Server Status: {status_report}")
        
    return variations


def showlayout(n: int = 1, label: Optional[List[str]] = None):
    """Shows a matplotlib plot of the n-th layout variation."""
    global _layout_variations
    if not _layout_variations or n < 1 or n > len(_layout_variations):
        print(f"Variation {n} does not exist. Available variations: {len(_layout_variations)}")
        return
        
    layout = _layout_variations[n - 1]["layout"]
    score = _layout_variations[n - 1]["score"]
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("Please install matplotlib to use showlayout(): pip install matplotlib")
        return

    fig, ax = plt.subplots()
    
    global _site
    if _site is not None and getattr(_site, 'points', None):
        site_pts = [(pt['x'], pt['y']) for pt in _site.points]
        poly = patches.Polygon(site_pts, closed=True, fill=False, edgecolor='red', linestyle='--', linewidth=2)
        ax.add_patch(poly)
        
    if label is None:
        label = ["name"]
        
    total_area = 0.0
    for r in layout:
        color = getattr(r, 'color', '#ffffff')
        rect = patches.Rectangle((r.x, r.y), r.w, r.h, linewidth=1, edgecolor='black', facecolor=color, alpha=0.8)
        ax.add_patch(rect)
        label_parts = []
        unit_str = "m" if _settings["unit"] == "m" else "ft"
        sq_unit_str = "sq.m" if _settings["unit"] == "m" else "sq.ft"
        
        calc_area = round(r.w * r.h, 1) if r.w and r.h else 0.0
        total_area += calc_area
        
        if "name" in label:
            label_parts.append(r.name or r.id)
        if "id" in label:
            label_parts.append(r.id)
        if "dim" in label:
            label_parts.append(f"{r.w}x{r.h}{unit_str}")
        if "area" in label:
            label_parts.append(f"{calc_area} {sq_unit_str}")
        
        text_str = "\n".join(label_parts)
        ax.text(r.x + r.w/2, r.y + r.h/2, text_str, ha='center', va='center', fontsize=8)

    ax.autoscale()
    plt.gca().set_aspect('equal', adjustable='box')
    plt.title(f"Rank {n} Variation (Score: {round(score, 1)})")
    fig.text(0.5, 0.02, f"Total Area = {round(total_area, 1)} {sq_unit_str}", ha='center', fontsize=10, fontweight='bold')
    plt.show(block=False)


def exportlayout(n: int = 1, filepath: str = "layout.json"):
    """Exports the n-th layout variation to JSON or DXF."""
    global _layout_variations
    if not _layout_variations or n < 1 or n > len(_layout_variations):
        print(f"Variation {n} does not exist.")
        return
        
    layout = _layout_variations[n - 1]["layout"]
    
    if filepath.lower().endswith(".json"):
        data = []
        for r in layout:
            r_dict = dataclasses.asdict(r)
            if r.x is not None and r.y is not None and r.w is not None and r.h is not None:
                r_dict["points"] = [
                    {"x": round(r.x, 2), "y": round(r.y, 2)}, 
                    {"x": round(r.x + r.w, 2), "y": round(r.y, 2)}, 
                    {"x": round(r.x + r.w, 2), "y": round(r.y + r.h, 2)}, 
                    {"x": round(r.x, 2), "y": round(r.y + r.h, 2)}
                ]
            data.append(r_dict)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Exported variation {n} to {os.path.abspath(filepath)}")
    elif filepath.lower().endswith(".dxf"):
        try:
            import ezdxf
        except ImportError:
            print("DXF export skipped (ezdxf not installed).")
            return
            
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        for r in layout:
            pts = [(r.x, r.y), (r.x + r.w, r.y), (r.x + r.w, r.y + r.h), (r.x, r.y + r.h)]
            msp.add_lwpolyline(pts, close=True)
            msp.add_text(r.name or r.id, dxfattribs={'height': 0.2}).set_placement((r.x + r.w/2, r.y + r.h/2))
                
        doc.saveas(filepath)
        print(f"Exported variation {n} to {os.path.abspath(filepath)}")
    else:
        print("Unsupported file format. Please use .json or .dxf")


def wait_for_plots():
    """Blocks execution until all matplotlib windows are closed by the user."""
    try:
        import matplotlib.pyplot as plt
        plt.show(block=True)
    except ImportError:
        pass
