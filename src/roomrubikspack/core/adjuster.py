"""
core/adjuster.py

Post-placement gap snapping and edge alignment.

After the main layout generator has placed all rooms, small gaps between
adjacent rooms (caused by rounding or discrete grid sizing) can leave
unsightly slivers. The Adjuster performs two passes:

  Pass 1 — Gap snap    : if two rooms are within `gap_snap` metres of each other,
                         the smaller room's edge is extended to meet its neighbour.
  Pass 2 — Edge align  : if two adjacent room edges are nearly aligned (within
                         `gap_snap`), they are snapped to the same coordinate,
                         reducing the number of exterior corners in the building.

NOTE: All changes are collision-checked to ensure no room overlaps are introduced.
"""

from typing import List, Any


class Adjuster:
    """Static class providing post-placement layout refinement."""

    @staticmethod
    def adjust(rooms: List[Any], connections: List[Any], gap_snap: float) -> None:
        """
        Refines room placement by closing small gaps and aligning edges.

        Args:
            rooms    : list of Room objects with a 'domain' attribute [min_x, max_x, min_y, max_y]
            connections : adjacency connections (not directly used here, reserved for future use)
            gap_snap : maximum gap or misalignment (metres) that will be corrected
        """
        if not gap_snap or gap_snap <= 0:
            return  # No snapping requested

        # Collect all domain lists (each domain is a mutable [x0, x1, y0, y1])
        domains = [r.domain for r in rooms]

        def has_strict_overlap(pnts: List[float], current_idx: int) -> bool:
            """
            Checks if the proposed domain 'pnts' would strictly overlap any
            existing domain other than the one at 'current_idx'.
            Used to validate each adjustment before applying it.
            """
            epsilon = 0.05
            for k, d in enumerate(domains):
                if k == current_idx:
                    continue  # Don't compare a room against itself
                x_overlap = pnts[0] + epsilon < d[1] and pnts[1] - epsilon > d[0]
                y_overlap = pnts[2] + epsilon < d[3] and pnts[3] - epsilon > d[2]
                if x_overlap and y_overlap:
                    return True  # This adjustment would cause an overlap
            return False

        # ---------------------------------------------------------------
        # Pass 1: Gap snap — extend room edges to close small gaps
        # Runs twice to catch gaps that open up after earlier adjustments
        # ---------------------------------------------------------------
        for _ in range(2):
            for i in range(len(domains)):
                for j in range(len(domains)):
                    if i == j:
                        continue

                    a = domains[i]  # Domain being potentially adjusted
                    b = domains[j]  # Neighbour domain
                    room_a = rooms[i]

                    # --- Horizontal snap (close X gap when rooms share a Y range) ---
                    y_overlap = max(a[2], b[2]) < min(a[3], b[3]) - 0.1  # Rooms share a Y span
                    if y_overlap:
                        dx_ab = b[0] - a[1]   # Gap: b is to the right of a
                        if 0 < dx_ab <= gap_snap:
                            expanded = [a[0], b[0], a[2], a[3]]  # Proposed expanded domain
                            if not has_strict_overlap(expanded, i):
                                a[1] = b[0]                    # Extend a's right edge to meet b
                                room_a.w = a[1] - a[0]         # Update room width

                        dx_ba = a[0] - b[1]   # Gap: a is to the right of b
                        if 0 < dx_ba <= gap_snap:
                            expanded = [b[1], a[1], a[2], a[3]]
                            if not has_strict_overlap(expanded, i):
                                a[0] = b[1]                    # Extend a's left edge to meet b
                                room_a.w = a[1] - a[0]

                    # --- Vertical snap (close Y gap when rooms share an X range) ---
                    x_overlap = max(a[0], b[0]) < min(a[1], b[1]) - 0.1  # Rooms share an X span
                    if x_overlap:
                        dy_ab = b[2] - a[3]   # Gap: b is above a
                        if 0 < dy_ab <= gap_snap:
                            expanded = [a[0], a[1], a[2], b[2]]
                            if not has_strict_overlap(expanded, i):
                                a[3] = b[2]                    # Extend a's top edge to meet b
                                room_a.h = a[3] - a[2]         # Update room height

                        dy_ba = a[2] - b[3]   # Gap: a is above b
                        if 0 < dy_ba <= gap_snap:
                            expanded = [a[0], a[1], b[3], a[3]]
                            if not has_strict_overlap(expanded, i):
                                a[2] = b[3]                    # Extend a's bottom edge to meet b
                                room_a.h = a[3] - a[2]

        # ---------------------------------------------------------------
        # Pass 2: Edge alignment — align nearly-matching edges to reduce corners
        # ---------------------------------------------------------------
        for i in range(len(domains)):
            for j in range(len(domains)):
                if i == j:
                    continue

                a = domains[i]
                b = domains[j]
                room_a = rooms[i]

                # Do these rooms share an X range (horizontally adjacent or overlapping)?
                x_adjacent = max(a[0], b[0]) <= min(a[1], b[1]) + 0.1
                # Do these rooms share a Y range (vertically adjacent or overlapping)?
                y_adjacent = max(a[2], b[2]) <= min(a[3], b[3]) + 0.1

                if x_adjacent:
                    # Align top edges: if a's top is close to b's top, snap upward
                    if 0 < abs(a[3] - b[3]) <= gap_snap:
                        if a[3] < b[3]:  # a is slightly shorter than b
                            expanded = [a[0], a[1], a[2], b[3]]
                            if not has_strict_overlap(expanded, i):
                                a[3] = b[3]
                                room_a.h = a[3] - a[2]

                    # Align bottom edges: if a's bottom is close to b's bottom, snap downward
                    if 0 < abs(a[2] - b[2]) <= gap_snap:
                        if a[2] > b[2]:  # a starts slightly higher than b
                            expanded = [a[0], a[1], b[2], a[3]]
                            if not has_strict_overlap(expanded, i):
                                a[2] = b[2]
                                room_a.h = a[3] - a[2]

                if y_adjacent:
                    # Align right edges: if a's right is close to b's right, snap rightward
                    if 0 < abs(a[1] - b[1]) <= gap_snap:
                        if a[1] < b[1]:  # a is slightly narrower on the right
                            expanded = [a[0], b[1], a[2], a[3]]
                            if not has_strict_overlap(expanded, i):
                                a[1] = b[1]
                                room_a.w = a[1] - a[0]

                    # Align left edges: if a's left is close to b's left, snap leftward
                    if 0 < abs(a[0] - b[0]) <= gap_snap:
                        if a[0] > b[0]:  # a starts slightly further right than b
                            expanded = [b[0], a[1], a[2], a[3]]
                            if not has_strict_overlap(expanded, i):
                                a[0] = b[0]
                                room_a.w = a[1] - a[0]
