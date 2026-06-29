"""
roomrubikspack/types.py

Defines the core data structures used throughout the layout engine.
These are primarily implemented as standard Python `dataclasses` to enforce strict
type checking and maintain a clean schema for serialising/deserialising JSON
payloads when working with APIs or saving state.

Classes:
    Room: Represents a single rectangular space in the floorplan.
    Connection: Represents an adjacency requirement between two rooms.
    Site: Represents a bounding polygon that constraints the layout.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class Room:
    """
    Core room model.
    A room can either have explicit dimensions (w, h) or just an area —
    dimensiongen() will resolve the latter into w/h automatically.
    """
    id: str                                     # Unique room identifier (user-defined)
    name: str = ""                              # Human-readable room label
    x: float = 0.0                              # Initial X position hint (metres); refined by GA
    y: float = 0.0                              # Initial Y position hint (metres); refined by GA
    w: Optional[float] = None                   # Width (metres); set by user or dimensiongen()
    h: Optional[float] = None                   # Height (metres); set by user or dimensiongen()
    area: Optional[float] = None                # Target floor area in m²; triggers auto-dimensioning
    color: str = "#ffffff"                      # Display fill colour
    attached: bool = False                      # True = placed inside/onto a parent room
    startSpace: bool = False                    # True = entry point; exactly one room must be True
    attachedSpace: bool = False                 # True = user-declared dependent room (e.g. en-suite)


@dataclass
class Connection:
    """
    Represents an adjacency requirement between two rooms.
    The layout engine tries to place roomA and roomB with a shared wall.
    """
    roomA: str                  # ID of the first room
    roomB: str                  # ID of the second room
    id: Optional[str] = None    # Auto-generated as "roomA_roomB" if not provided

    def __post_init__(self):
        # Auto-generate a stable connection ID if the user didn't supply one
        if self.id is None:
            self.id = f"{self.roomA}_{self.roomB}"


@dataclass
class Site:
    """
    Optional outer site boundary polygon.
    If defined, the layout engine can attempt to fit the rooms within it.
    """
    points: List[Dict[str, float]]  # List of {x, y} dicts defining the polygon vertices
    width: Optional[float] = None   # Bounding width of the site (derived or explicit)
    height: Optional[float] = None  # Bounding height of the site (derived or explicit)
    layerId: Optional[str] = None   # Drawing layer for the site polygon
    offsets: Optional[List[float]] = None  # Setback distances [top, right, bottom, left]
