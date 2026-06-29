"""
roomrubikspack/utils/constraints.py

Constraint system for the roomrubikspack layout engine.

Constraints are custom user-defined rules (like "Master Bed must be North").
The GA does NOT hard-reject layouts that violate constraints — it just scores them
more poorly, so they tend to be eliminated over successive generations.

Supported constraint types:
    "position"  — Biases a specific room toward a compass quadrant (N, S, E, W, NE, NW, SE, SW, B).
    "area"      — Penalises layouts whose total footprint differs from a target area (m²).
    "perimeter" — Penalises layouts with a large bounding box perimeter (encourages compactness).
"""

from typing import List, Dict, Any, Optional
import math
from ..types import Room

# Module-level list that stores all registered constraints for the current session
_global_constraints: List[Dict[str, Any]] = []


def add_constraint(constraint_type: str, room_id: Optional[str] = None, value: Any = None):
    """
    Appends a new constraint to the global constraint list.
    Called internally by rr.constraint().
    """
    _global_constraints.append({
        "type": constraint_type,   # One of: "position", "area", "perimeter"
        "room_id": room_id,        # Target room for positional constraints; None for global ones
        "value": value             # Meaning depends on type (see module docstring)
    })


def clear_constraints():
    """Resets the global constraint list. Called by rr.init() at session start."""
    global _global_constraints
    _global_constraints = []


def get_sector_coordinates(sector: str, xlim: float, ylim: float) -> Dict[str, float]:
    """
    Converts a compass sector string into an (x, y) target coordinate within
    the layout bounding box. Used during pre-adjustment to seed initial room positions.

    The layout centre is (xlim/2, ylim/2).
    Sectors are offset by 28% of the layout size in the respective direction.

    Args:
        sector : compass direction — N, S, E, W, NE, NW, SE, SW, or B (centre)
        xlim   : total layout width (metres)
        ylim   : total layout height (metres)
    """
    cx = xlim / 2.0     # Centre X of the layout
    cy = ylim / 2.0     # Centre Y of the layout
    rx = xlim * 0.28    # Offset radius in X direction
    ry = ylim * 0.28    # Offset radius in Y direction

    # Map each compass direction to an (x, y) coordinate
    if sector == 'NE': return {"x": cx + rx, "y": cy + ry}
    elif sector == 'NW': return {"x": cx - rx, "y": cy + ry}
    elif sector == 'SE': return {"x": cx + rx, "y": cy - ry}
    elif sector == 'SW': return {"x": cx - rx, "y": cy - ry}
    elif sector == 'N':  return {"x": cx,       "y": cy + ry}
    elif sector == 'S':  return {"x": cx,       "y": cy - ry}
    elif sector == 'E':  return {"x": cx + rx,  "y": cy}
    elif sector == 'W':  return {"x": cx - rx,  "y": cy}
    else:                return {"x": cx,       "y": cy}  # 'B' = centre


def preadjust_rooms_for_constraints(rooms: List[Room], xlim: float, ylim: float, constraints: Optional[List[Dict[str, Any]]] = None) -> List[Room]:
    """
    Pre-adjusts room starting positions before the GA begins, based on positional constraints.
    Rooms with a 'position' constraint get their (x, y) seeded near the target sector,
    giving the layout engine a warm-start hint toward satisfying that constraint.

    Multiple rooms in the same sector are staggered (offset) so they don't all start
    at exactly the same point, which would cause collision resolution failures.

    Args:
        rooms : list of Room objects (modified in-place)
        xlim  : layout width limit (metres)
        ylim  : layout height limit (metres)
        constraints : Optional list of constraints. If None, uses module-level constraints.
    """
    staggered_count: Dict[str, int] = {}  # Tracks how many rooms already placed in each sector
    active_constraints = constraints if constraints is not None else _global_constraints

    for r in rooms:
        # Look up any position constraint for this specific room
        pos_constraint = next(
            (c for c in active_constraints if c["type"] == "position" and c["room_id"] == r.id),
            None
        )
        if pos_constraint:
            sector = str(pos_constraint["value"]).upper()
            target = get_sector_coordinates(sector, xlim, ylim)

            # Calculate a stagger offset so rooms in the same sector don't overlap at start
            if sector not in staggered_count:
                staggered_count[sector] = 0
            stagger_index = staggered_count[sector]
            staggered_count[sector] += 1

            # Grid stagger: up to 3 columns × N rows, each 2m apart
            stagger_x = ((stagger_index % 3) - 1) * 2.0
            stagger_y = (math.floor(stagger_index / 3) - 1) * 2.0

            # Centre the room on the target position then apply stagger
            r.x = target["x"] - (r.w or 0) / 2.0 + stagger_x
            r.y = target["y"] - (r.h or 0) / 2.0 + stagger_y

    return rooms


def evaluate_constraints_penalty(layout: List[Room], xlim: float, ylim: float, constraints: Optional[List[Dict[str, Any]]] = None) -> float:
    """
    Calculates a scalar penalty score representing how well the given layout
    satisfies all registered constraints. A lower score is better.
    The penalty is added to the GA scoring function in elitist_genetic_algorithm.py.

    Penalty breakdown by constraint type:
        "position"  : distance from room centre to the target sector × 150
        "area"      : absolute difference from target total area × 10
        "perimeter" : bounding box perimeter × 5 (encourages compact layouts)

    Args:
        layout : list of placed Room objects with x, y, w, h set
        xlim   : layout width (used for normalisation)
        ylim   : layout height (used for normalisation)
        constraints : Optional list of constraints. If None, uses module-level constraints.
    """
    if not layout:
        return 0.0

    # Compute the bounding box of all placed rooms
    min_x = float('inf');  max_x = float('-inf')
    min_y = float('inf');  max_y = float('-inf')
    for r in layout:
        if r.x < min_x: min_x = r.x
        if r.x + (r.w or 0) > max_x: max_x = r.x + (r.w or 0)
        if r.y < min_y: min_y = r.y
        if r.y + (r.h or 0) > max_y: max_y = r.y + (r.h or 0)

    if min_x == float('inf'):
        return 0.0  # Empty layout

    lw = max(1.0, max_x - min_x)  # Avoid division by zero
    lh = max(1.0, max_y - min_y)

    # Calculate the area-weighted centroid of the layout (centroid of the plinthline)
    total_area = 0.0
    sum_cx = 0.0
    sum_cy = 0.0
    for r in layout:
        area = (r.w or 0) * (r.h or 0)
        cx = r.x + (r.w or 0) / 2.0
        cy = r.y + (r.h or 0) / 2.0
        sum_cx += cx * area
        sum_cy += cy * area
        total_area += area

    if total_area > 0:
        layout_center_x = sum_cx / total_area
        layout_center_y = sum_cy / total_area
    else:
        layout_center_x = (min_x + max_x) / 2.0
        layout_center_y = (min_y + max_y) / 2.0

    total_penalty = 0.0
    active_constraints = constraints if constraints is not None else _global_constraints

    for c in active_constraints:
        ctype = c["type"]
        val = c["value"]

        if ctype == "position":
            # Positional bias: penalise if the room's centre is not in the right quadrant
            room_id = c["room_id"]
            r = next((rm for rm in layout if rm.id == room_id), None)
            if not r:
                continue  # Room not in this layout (e.g. if it was unplaced)

            sector = str(val).upper()
            # Room centre offset from layout centre
            rx = (r.x + (r.w or 0) / 2.0) - layout_center_x
            ry = (r.y + (r.h or 0) / 2.0) - layout_center_y

            # Normalise offsets to ±0.5 range for sector comparison
            norm_x = rx / lw
            norm_y = ry / lh
            tolerance = 0.08  # Allow a small margin before penalising

            # Check if the room already satisfies the sector
            is_valid = False
            if sector == 'NE': is_valid = norm_x >= -tolerance and norm_y >= -tolerance
            elif sector == 'NW': is_valid = norm_x <= tolerance and norm_y >= -tolerance
            elif sector == 'SE': is_valid = norm_x >= -tolerance and norm_y <= tolerance
            elif sector == 'SW': is_valid = norm_x <= tolerance and norm_y <= tolerance
            elif sector == 'N':  is_valid = norm_y >= -tolerance
            elif sector == 'S':  is_valid = norm_y <= tolerance
            elif sector == 'E':  is_valid = norm_x >= -tolerance
            elif sector == 'W':  is_valid = norm_x <= tolerance
            elif sector == 'B':  is_valid = abs(norm_x) < 0.2 and abs(norm_y) < 0.2

            if not is_valid:
                # Compute the ideal target offset for this sector
                rx_target = lw * 0.25
                ry_target = lh * 0.25
                target_x = target_y = 0.0

                if sector == 'NE': target_x = rx_target;  target_y = ry_target
                elif sector == 'NW': target_x = -rx_target; target_y = ry_target
                elif sector == 'SE': target_x = rx_target;  target_y = -ry_target
                elif sector == 'SW': target_x = -rx_target; target_y = -ry_target
                elif sector == 'N': target_y = ry_target
                elif sector == 'S': target_y = -ry_target
                elif sector == 'E': target_x = rx_target
                elif sector == 'W': target_x = -rx_target

                # Euclidean distance from current position to ideal target
                dist = math.hypot(rx - target_x, ry - target_y)
                total_penalty += dist * 150.0  # High weight — position is a strong constraint

        elif ctype == "area":
            # Area constraint: penalise total footprint deviation from target
            try:
                target_area = float(val)
                diff = abs(total_area - target_area)
                total_penalty += diff * 10.0   # Moderate weight
            except (ValueError, TypeError):
                pass  # Ignore malformed constraint values

        elif ctype == "perimeter":
            if str(val).lower() == "minimize":
                # Perimeter constraint: penalise large bounding boxes to encourage compactness
                bbox_perimeter = 2 * (lw + lh)
                total_penalty += bbox_perimeter * 5.0  # Low weight — this is a preference, not a rule

    return total_penalty
