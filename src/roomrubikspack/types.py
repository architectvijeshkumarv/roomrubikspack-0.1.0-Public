"""
types.py

Defines all shared dataclasses (data models) used throughout the package.
These act as plain data containers — no methods or business logic lives here.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Window:
    """Represents a window element placed inside a room."""
    id: str                         # Unique window identifier
    worldX: float                   # X position in world coordinates (metres)
    worldY: float                   # Y position in world coordinates (metres)
    widthM: float                   # Width of the window opening (metres)
    lengthM: float                  # Depth/thickness of the window (metres)
    isVertical: bool                # True = window sits on a vertical (N/S) wall
    sillHeight: Optional[float] = None  # Height of the window sill from floor level


@dataclass
class Door:
    """Represents a door element placed inside a room."""
    id: str                         # Unique door identifier
    worldX: float                   # X position in world coordinates (metres)
    worldY: float                   # Y position in world coordinates (metres)
    widthM: float                   # Clear opening width (metres)
    lengthM: float                  # Door panel depth (metres)
    isVertical: bool                # True = door sits on a vertical (N/S) wall
    isMain: Optional[bool] = False          # True = main entrance door
    isOpening: Optional[bool] = False       # True = opening only (no panel drawn)
    hingeX: Optional[float] = None          # X coordinate of the hinge pivot
    hingeY: Optional[float] = None          # Y coordinate of the hinge pivot
    swingDirX: Optional[float] = None       # X component of the swing direction vector
    swingDirY: Optional[float] = None       # Y component of the swing direction vector
    _candidates: Optional[List[Any]] = None # Internal: candidate placement positions
    _candidateIdx: Optional[int] = None     # Internal: chosen candidate index
    doorCount: Optional[int] = None         # Number of doors in a multi-leaf set


@dataclass
class Furniture:
    """Represents a furniture item placed inside a room."""
    id: str                             # Unique furniture identifier
    type: str                           # Category string e.g. "bed", "desk", "sofa"
    worldX: float                       # X position in world coordinates (metres)
    worldY: float                       # Y position in world coordinates (metres)
    widthM: float                       # Width of the furniture piece (metres)
    lengthM: float                      # Length of the furniture piece (metres)
    rotation: float                     # Rotation angle in degrees (0 = facing right)
    color: Optional[str] = None         # Hex fill colour for rendering
    mirrored: Optional[bool] = False    # True = horizontally flipped
    isResponsiveSet: Optional[bool] = False  # True = part of a responsive furniture set


@dataclass
class Room:
    """
    Core room model.
    A room can either have explicit dimensions (w, h) or just an area —
    dimensiongen() will resolve the latter into w/h automatically.
    """
    id: str                                     # Unique room identifier (user-defined)
    name: str = ""                              # Human-readable room label
    x: float = 0.0                             # Initial X position hint (metres); refined by GA
    y: float = 0.0                             # Initial Y position hint (metres); refined by GA
    w: Optional[float] = None                  # Width (metres); set by user or dimensiongen()
    h: Optional[float] = None                  # Height (metres); set by user or dimensiongen()
    area: Optional[float] = None               # Target floor area in m²; triggers auto-dimensioning
    color: str = "#ffffff"                      # Display fill colour
    attached: bool = False                      # True = placed inside/onto a parent room
    startSpace: bool = False                    # True = entry point; exactly one room must be True
    attachedSpace: bool = False                 # True = user-declared dependent room (e.g. en-suite)
    isCorridor: Optional[bool] = False          # True = corridor strip (auto-created by layout engine)
    wallPresent: Optional[bool] = True          # False = room boundary is open (no wall drawn)
    doors: Optional[List[Door]] = field(default_factory=list)       # Doors on this room's walls
    windows: Optional[List[Window]] = field(default_factory=list)   # Windows on this room's walls
    furniture: Optional[List[Furniture]] = field(default_factory=list)  # Furniture inside the room
    labelOffsetX: Optional[float] = None        # Fine-tune label X offset for rendering
    labelOffsetY: Optional[float] = None        # Fine-tune label Y offset for rendering
    levelId: Optional[str] = None              # Floor/level this room belongs to
    layerId: Optional[str] = None              # Drawing layer identifier
    nameFontSize: Optional[float] = None        # Override name label font size
    dimFontSize: Optional[float] = None         # Override dimension label font size
    areaFontSize: Optional[float] = None        # Override area label font size
    wfr: Optional[float] = None                # Window-to-floor ratio (used in daylighting calc)
    activityDbA: Optional[float] = None         # Acoustic activity level in dBA
    lightingTargetLux: Optional[float] = None   # Daylighting target illuminance (lux)
    lightingTargetHours: Optional[float] = None # Required daylighting hours per day
    unconnectedHeight: Optional[float] = None   # Ceiling height if disconnected from standard storey
    topLevelId: Optional[str] = None           # Top-most level if the room spans multiple levels
    windowRegenCount: Optional[int] = None      # Number of times windows have been regenerated


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


@dataclass
class Road:
    """
    Represents a road or access path adjacent to the site.
    Used for orientation and entry point determination.
    """
    id: str                             # Unique road identifier
    points: List[Dict[str, float]]      # Centreline polyline as list of {x, y}
    width: float                        # Road width in metres
    direction: Optional[str] = None     # Cardinal direction of the road (N, S, E, W)
    layerId: Optional[str] = None       # Drawing layer identifier
    isInternal: Optional[bool] = False  # True = internal driveway or pedestrian path
