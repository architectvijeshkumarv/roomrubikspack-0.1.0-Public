"""
roomrubikspack/core/generator.py

This module provides the high-level orchestration for generating a single layout variation.
It processes the connectivity graph, determines the optimal placement order of rooms
using Breadth-First Search (BFS) from the start room, and delegates the actual 
coordinate assignment and collision resolution to the LayoutGenerator class.

Functions:
  - count_corners: measures architectural complexity (external corner count)
  - calculate_perimeter: measures layout compactness (net external perimeter)
  - generate_layout: delegates to LayoutGenerator and post-processes the result
"""
from typing import List, Dict, Any, Set, Optional
import copy
from .layout_generator import LayoutGenerator


def count_corners(rooms: List[Any]) -> int:
    """
    Counts the number of architectural corners in the combined building footprint.

    The algorithm creates a grid of every unique X and Y coordinate boundary across
    all rooms, then checks each grid intersection point to determine how many room
    quadrants are occupied. The occupancy pattern determines whether the point is
    a convex corner (count=1,3) or a diagonal notch (count=2 with Q1+Q3 or Q2+Q4).

    Fewer corners → simpler building outline → lower construction complexity.
    This value is used as part of the GA scoring function.
    """
    # Collect all unique X and Y wall coordinates
    xs: Set[float] = set()
    ys: Set[float] = set()
    for r in rooms:
        xs.add(r.x);       xs.add(r.x + r.w)
        ys.add(r.y);       ys.add(r.y + r.h)

    corners = 0
    epsilon = 0.01  # Floating-point tolerance for boundary detection

    for x in xs:
        for y in ys:
            # Check the four quadrants around each grid intersection
            # q1=NE, q2=NW, q3=SW, q4=SE (looking from the intersection point)
            q1 = q2 = q3 = q4 = False
            for r in rooms:
                # q1: room occupies the right+up quadrant from (x,y)
                if r.x <= x + epsilon and r.x + r.w >= x + epsilon and r.y <= y + epsilon and r.y + r.h >= y + epsilon: q1 = True
                # q2: room occupies the left+up quadrant
                if r.x <= x - epsilon and r.x + r.w >= x - epsilon and r.y <= y + epsilon and r.y + r.h >= y + epsilon: q2 = True
                # q3: room occupies the left+down quadrant
                if r.x <= x - epsilon and r.x + r.w >= x - epsilon and r.y <= y - epsilon and r.y + r.h >= y - epsilon: q3 = True
                # q4: room occupies the right+down quadrant
                if r.x <= x + epsilon and r.x + r.w >= x + epsilon and r.y <= y - epsilon and r.y + r.h >= y - epsilon: q4 = True

            count = (1 if q1 else 0) + (1 if q2 else 0) + (1 if q3 else 0) + (1 if q4 else 0)
            # 1 or 3 filled quadrants = exterior corner (convex or re-entrant)
            if count == 1 or count == 3:
                corners += 1
            # 2 diagonally opposite quadrants filled = two corners (notch in the outline)
            elif count == 2 and ((q1 and q3) or (q2 and q4)):
                corners += 2

    return corners


def calculate_perimeter(rooms: List[Any]) -> float:
    """
    Calculates the net external perimeter of the combined building footprint.

    Method:
      Total perimeter = sum of all individual room perimeters
      Minus shared wall segments (walls that appear on two adjacent rooms are interior)

    A smaller perimeter indicates a more compact layout (preferred by GA scoring).
    """
    # Sum all individual room perimeters
    total_perimeter = sum(2 * (r.w + r.h) for r in rooms)

    # Subtract shared wall lengths (walls between adjacent rooms)
    shared_perimeter = 0.0
    epsilon = 0.1
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            r1 = rooms[i]
            r2 = rooms[j]

            overlap_x = max(0.0, min(r1.x + r1.w, r2.x + r2.w) - max(r1.x, r2.x))
            overlap_y = max(0.0, min(r1.y + r1.h, r2.y + r2.h) - max(r1.y, r2.y))

            # Horizontal adjacency (rooms touch vertically)
            if abs(r1.y + r1.h - r2.y) < epsilon or abs(r2.y + r2.h - r1.y) < epsilon:
                if overlap_x > 0:
                    shared_perimeter += 2 * overlap_x

            # Vertical adjacency (rooms touch horizontally)
            if abs(r1.x + r1.w - r2.x) < epsilon or abs(r2.x + r2.w - r1.x) < epsilon:
                if overlap_y > 0:
                    shared_perimeter += 2 * overlap_y

    return total_perimeter - shared_perimeter

def generate_layout(rooms: List[Any], connections: List[Any], settings: Dict[str, Any], start_room_id: str, site_points: Optional[List[Dict[str, float]]] = None) -> List[Any]:
    final_rooms = []
    dim_gen = None
    if "base_grid_sizes" in settings:
        from ..generators.dimension_generator import DimensionGenerator
        dim_gen = DimensionGenerator(
            base_grid_sizes=settings.get("base_grid_sizes"),
            area_variation=settings.get("areaVariation", 0.2),
            max_aspect_ratio=settings.get("maxAspectRatio", 1.5)
        )

    # Delegate to LayoutGenerator with randomised parent selection for variety
    generator = LayoutGenerator(0.5, dim_gen)
    layout = generator.generate_layout(rooms, connections, start_room_id, {
        "locationVariation": settings.get("locationVariation", 0),
        "gapSnap": settings.get("gapSnap", settings.get("allowedSpaceGap", 0)),
        "randomizeParents": True  # Enables random BFS ordering for layout diversity
    })

    if layout:
        final_rooms = layout
    else:
        final_rooms = rooms  # Fallback: return unplaced rooms on complete failure

    if final_rooms:
        # Compute bounding box of all placed rooms
        min_x = min(r.x for r in final_rooms)
        min_y = min(r.y for r in final_rooms)
        max_x = max(r.x + r.w for r in final_rooms)
        max_y = max(r.y + r.h for r in final_rooms)

        layout_w = max_x - min_x
        layout_h = max_y - min_y

        # Default: shift layout so it starts 1m from origin
        shift_x = -min_x + 1
        shift_y = -min_y + 1

        # Override: centre the layout within the site bounds if provided
        xlim = settings.get("xlim")
        ylim = settings.get("ylim")
        if site_points:
            site_min_x = min(p['x'] for p in site_points)
            site_max_x = max(p['x'] for p in site_points)
            site_min_y = min(p['y'] for p in site_points)
            site_max_y = max(p['y'] for p in site_points)
            site_w = site_max_x - site_min_x
            site_h = site_max_y - site_min_y
            shift_x = site_min_x + (site_w - layout_w) / 2 - min_x
            shift_y = site_min_y + (site_h - layout_h) / 2 - min_y
        elif xlim and ylim:
            shift_x = (xlim - layout_w) / 2 - min_x
            shift_y = (ylim - layout_h) / 2 - min_y

        # Apply the shift to all rooms and round to 1 decimal place for neatness
        for r in final_rooms:
            r.x = round(r.x + shift_x, 1)
            r.y = round(r.y + shift_y, 1)
            if r.w is not None: r.w = round(r.w, 1)
            if r.h is not None: r.h = round(r.h, 1)

    return final_rooms
