"""
roomrubikspack/__init__.py

This is the primary public API for the RoomRubiks procedural floorplan layout engine.
It maintains the global session state (rooms, connections, settings, site boundaries) 
and orchestrates the core procedural generation pipeline (dimension generation, 
layout placement via Genetic Algorithm, and visualization).

Users interact with this module using the `rr.*` namespace (e.g., `rr.room()`, `rr.connectivity()`).
"""

from typing import List, Dict, Tuple, Optional, Any
import json
import dataclasses
import math
import os

def calculate_ga_parameters(max_variations: int, selv: int = 0):
    base_pop = int(50 + (30 * math.log2(max_variations + 1)))
    base_gen = int(10 + (5 * math.log10(max_variations + 1)))
    
    if selv > 0:
        population_size = int(base_pop * 0.6)
        generations = int(base_gen * 5.0)
    else:
        population_size = base_pop
        generations = base_gen
        
    population_size = min(population_size, 500)
    generations = min(generations, 150)
    
    return population_size, generations

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
_settings: Dict[str, Any] = {"unit": "m", "vastu": False}

# Configurable server URL (falls back to live Cloud Run or environment variable)



def deserialize_room(r: Dict[str, Any]) -> Room:
    """
    Safely parses a dictionary of room attributes into a Room dataclass object.
    Filters out any unexpected keys that aren't defined in the Room dataclass schema.
    """
    valid_fields = {f.name for f in dataclasses.fields(Room)}
    filtered_data = {k: v for k, v in r.items() if k in valid_fields}
    return Room(**filtered_data)


def _union_area(rooms) -> float:
    """
    Computes the true union area of all axis-aligned room rectangles.
    Uses a coordinate-compression sweep to avoid double-counting
    attached rooms that are geometrically inside their parent room.
    """
    rects = [(r.x, r.y, r.x + r.w, r.y + r.h) for r in rooms if r.w and r.h]
    if not rects:
        return 0.0

    # Collect all unique X coordinates and sort them
    xs = sorted(set(x for x0, _, x1, _ in rects for x in (x0, x1)))
    # Collect all unique Y coordinates and sort them
    ys = sorted(set(y for _, y0, _, y1 in rects for y in (y0, y1)))

    total = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx = (xs[i] + xs[i + 1]) / 2  # Centre of this cell
            cy = (ys[j] + ys[j + 1]) / 2
            # If ANY room covers this cell, count it exactly once
            covered = any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in rects)
            if covered:
                total += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return round(total, 1)


def init():
    """
    Initializes or resets a new RoomRubiks session.
    
    This function clears all global state variables, ensuring that consecutive
    runs or iterative generation attempts start with a clean slate without
    residual data from previous executions.
    """
    global _rooms, _connections, _site, _dim_gen, _layout_variations, _base_grid_sizes
    _rooms = []
    _connections = []
    _site = None
    _dim_gen = None
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


def connectivityshow(filepath: Optional[str] = None):
    """Shows a matplotlib network diagram of the registered connectivity. If filepath is provided, saves to disk instead of showing UI."""
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
    plt.axis('off')
    
    if filepath:
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Network diagram saved to {filepath}")
        plt.close()
    else:
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


def settings(unit: str = "m"):
    """Configures global settings."""
    global _settings
    if unit in ["m", "ft"]:
        _settings["unit"] = unit
        print(f"Settings updated: unit set to '{unit}'")
    else:
        print("Invalid unit. Use 'm' or 'ft'.")


def vastu(enable: bool = False):
    """Enables or disables Vastu Shastra compliance checks during layout generation."""
    global _settings
    _settings["vastu"] = enable
    state = "enabled" if enable else "disabled"
    print(f"Vastu compliance is now {state}.")


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
    """Calculates optimal dimensions for rooms missing them using the local DimensionGenerator."""
    global _rooms, _base_grid_sizes
    
    print(f"Generating optimal dimensions locally...")
    from .generators.dimension_generator import DimensionGenerator
    
    dim_gen = DimensionGenerator(base_grid_sizes=_base_grid_sizes, area_variation=avar, max_aspect_ratio=mar)
    
    saved_dimensions = {}
    for r in _rooms:
        if getattr(r, 'area', None) and (getattr(r, 'w', None) is None or getattr(r, 'h', None) is None):
            best_dim = dim_gen.get_best_dimension(r.area)
            if best_dim:
                r.w = best_dim["w"]
                r.h = best_dim["h"]
                saved_dimensions[r.id] = best_dim
    
    print(f"Generated optimal dimensions for {len(saved_dimensions)} rooms.")
    return saved_dimensions



def generatelayout(lvar: float = 0.5, sgap: float = 1.0, max_variations: int = 10, liked_layouts: Optional[List[Any]] = None, selv: Optional[int] = None):
    """Generates the architectural layouts using the local Elitist Genetic Algorithm."""
    global _rooms, _connections, _site, _settings, _layout_variations
    print(f"Generating layout locally with location_variation={lvar}, allowed_space_gap={sgap}...")
    
    from .utils.constraints import _global_constraints
    from .core.elitist_genetic_algorithm import ElitistGeneticAlgorithm
    
    # Add grid sizes to settings
    gen_settings = _settings.copy()
    gen_settings["base_grid_sizes"] = _base_grid_sizes
    gen_settings["useCorridors"] = False
    gen_settings["locationVariation"] = lvar
    gen_settings["allowedSpaceGap"] = sgap
    gen_settings["otherDoorWidth"] = 0.9

    start_spaces = [r for r in _rooms if r.startSpace]
    start_room_id = start_spaces[0].id if start_spaces else _rooms[0].id
    
    # Handle Explore then Exploit (selv) target topology extraction
    if selv is not None and _layout_variations and 1 <= selv <= len(_layout_variations):
        target_topology_layout = _layout_variations[selv - 1]["layout"]
        gen_settings["target_topology_layout"] = target_topology_layout
        print(f"DEEP REFINEMENT ACTIVATED: Extracting topological signature from variation {selv}")
    elif selv is not None:
        print(f"WARNING: Invalid selv={selv}. Available variations: {len(_layout_variations)}. Ignoring selv.")

    # Initialize GA Engine Locally
    site_points = getattr(_site, 'points', None) if _site else None
    
    # Calculate parameters dynamically
    pop_size, gen_count = calculate_ga_parameters(max_variations, selv if selv is not None else 0)
    
    ga = ElitistGeneticAlgorithm(
        rooms=_rooms,
        connections=_connections,
        settings=gen_settings,
        start_room_id=start_room_id,
        pop_size=pop_size,
        max_generations=gen_count,
        constraints=_global_constraints,
        site_points=site_points
    )
    
    variations_data = ga.run_multiple(max_variations)
    
    if not variations_data:
        print("Failed to generate layouts.")
        return []
        
    _layout_variations = variations_data
    print(f"Successfully generated {len(_layout_variations)} unique variations (ranked best to worst).")
    
    for i, v in enumerate(_layout_variations):
        total_area = _union_area(v["layout"])
        v["total_area"] = total_area
        print(f"Rank {i+1} Variation - Score: {round(v['score'], 1)} - Total Area: {round(total_area, 1)} {gen_settings['unit']}²")
        
    return _layout_variations
def showlayout(n: int = 1, label: Optional[List[str]] = None, filepath: Optional[str] = None, shownetwork: bool = False):
    """
    Shows the n-th generated layout variation using Matplotlib.
    Optional label list configures text: ['name', 'id', 'dim', 'area']
    If filepath is provided, saves the image to disk.
    If shownetwork is True, plots the connectivity graph on the left and layout on the right.
    """
    global _layout_variations
    if not _layout_variations or n < 1 or n > len(_layout_variations):
        print(f"Variation {n} does not exist. Available variations: {len(_layout_variations)}")
        return
        
    layout = _layout_variations[n - 1]["layout"]
    score = _layout_variations[n - 1]["score"]
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        if shownetwork:
            import networkx as nx
    except ImportError:
        print("Please install matplotlib (and networkx if shownetwork=True) to use showlayout()")
        return

    if shownetwork:
        fig, (ax_net, ax) = plt.subplots(1, 2, figsize=(14, 6))
        
        G = nx.Graph()
        for r in _rooms:
            G.add_node(r.id, label=r.name or r.id, is_start=getattr(r, 'startSpace', False))
        for c in _connections:
            G.add_edge(c.roomA, c.roomB)
            
        # Position nodes based on the layout's actual coordinates
        pos = {}
        for r in layout:
            if r.x is not None and r.y is not None and r.w is not None and r.h is not None:
                pos[r.id] = (r.x + (r.w / 2), r.y + (r.h / 2))
            else:
                pos[r.id] = (0, 0)
        
        # Add any disconnected/unplaced rooms using spring layout fallback
        unplaced_nodes = [node for node in G.nodes() if node not in pos]
        if unplaced_nodes:
            fallback_pos = nx.spring_layout(G.subgraph(unplaced_nodes), seed=42)
            for node in unplaced_nodes:
                pos[node] = fallback_pos[node]
        labels_net = nx.get_node_attributes(G, 'label')
        colors_net = ['lightgreen' if nx.get_node_attributes(G, 'is_start').get(nd) else 'lightblue' for nd in G.nodes()]
        
        nx.draw(G, pos, ax=ax_net, labels=labels_net, node_color=colors_net, with_labels=True, node_size=2000, font_size=10, font_weight="bold", edge_color="gray")
        ax_net.set_title("Connectivity Network")
        ax_net.axis('off')
    else:
        fig, ax = plt.subplots()
    
    global _site
    if _site is not None and getattr(_site, 'points', None):
        site_pts = [(pt['x'], pt['y']) for pt in _site.points]
        poly = patches.Polygon(site_pts, closed=True, fill=False, edgecolor='red', linestyle='--', linewidth=2)
        ax.add_patch(poly)
        
    if label is None:
        label = ["name"]
        
    total_area = _union_area(layout)
    for r in layout:
        color = getattr(r, 'color', '#ffffff')
        rect = patches.Rectangle((r.x, r.y), r.w, r.h, linewidth=1, edgecolor='black', facecolor=color, alpha=0.8)
        ax.add_patch(rect)
        label_parts = []
        unit_str = "m" if _settings["unit"] == "m" else "ft"
        sq_unit_str = "sq.m" if _settings["unit"] == "m" else "sq.ft"
        
        calc_area = round(r.w * r.h, 1) if r.w and r.h else 0.0
        
        if "name" in label:
            label_parts.append(r.name or r.id)
        if "id" in label:
            label_parts.append(r.id)
        if "dim" in label:
            label_parts.append(f"{r.w}x{r.h}{unit_str}")
        if "area" in label:
            label_parts.append(f"{calc_area} {sq_unit_str}")
        if "vastu" in label:
            try:
                from .utils.vastu import get_vastu_rule_for_room
                vrule = get_vastu_rule_for_room(r.name or r.id)
                if vrule:
                    label_parts.append(f"Vastu: {vrule['primarySector']}")
            except ImportError:
                pass
        
        text_str = "\n".join(label_parts)
        ax.text(r.x + r.w/2, r.y + r.h/2, text_str, ha='center', va='center', fontsize=8)

    ax.autoscale()
    plt.gca().set_aspect('equal', adjustable='box')
    ax.axis('off')
    plt.title(f"Rank {n} Variation (Score: {round(score, 1)})")
    fig.text(0.5, 0.02, f"Total Area = {round(total_area, 1)} {sq_unit_str}", ha='center', fontsize=10, fontweight='bold')
    
    if filepath:
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Layout variation {n} saved to {filepath}")
        plt.close()
    else:
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
    """Utility to block script execution until all matplotlib figures are closed."""
    try:
        import matplotlib.pyplot as plt
        plt.show()
    except ImportError:
        pass

__all__ = [
    "init", "settings", "room", "site", "connectivity", "connectivityshow",
    "constraint", "vastu", "constructiongrid", "dimensiongen", "generatelayout",
    "showlayout", "exportlayout", "wait_for_plots", "add_constraint", "clear_constraints", "check_planarity"
]
