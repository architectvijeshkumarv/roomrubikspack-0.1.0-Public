"""
core/domain_subtractor.py

Computes the free (unoccupied) intervals along one axis of a rectangular domain
after subtracting all clashing (blocked) sub-domains.

This is the core geometric primitive used by PlaceChild to find valid X or Y
intervals where a new room can be positioned without overlapping existing rooms.

Example:
    Parent available domain spans X: 0 → 10.
    Existing rooms block X: 2→4 and 6→8.
    After subtraction, free intervals are: [(0,2), (4,6), (8,10)].
"""

from typing import List, Tuple

# Type alias for clarity: a domain is always [min_x, max_x, min_y, max_y]
Domain = Tuple[float, float, float, float]


class DomainSubtractor:
    """
    Subtracts a list of blocking domains from a parent domain along one axis,
    returning the remaining free intervals.
    """

    def __init__(self, parent: Domain, clashing_domains: List[Domain]):
        """
        Args:
            parent           : the full available rectangular zone
            clashing_domains : list of already-occupied zones that block placement
        """
        self.parent = parent
        self.clashing_domains = clashing_domains

    def subtract(self, axis: int = 0) -> List[Tuple[float, float]]:
        """
        Returns the free 1D intervals along the specified axis of the parent domain,
        after removing all clashing domain projections.

        Args:
            axis : 0 = project along X axis (use domain[0], domain[1])
                   1 = project along Y axis (use domain[2], domain[3])

        Returns:
            A sorted list of (start, end) tuples representing free intervals.
        """
        # Select the axis to project onto
        if axis == 0:
            main_min = self.parent[0]      # Parent's X start
            main_max = self.parent[1]      # Parent's X end
            get_coord = lambda rect: (rect[0], rect[1])  # Extract X span
        else:
            main_min = self.parent[2]      # Parent's Y start
            main_max = self.parent[3]      # Parent's Y end
            get_coord = lambda rect: (rect[2], rect[3])  # Extract Y span

        # Project all clashing domains onto the selected axis and sort by start position
        sub_intervals = [get_coord(rect) for rect in self.clashing_domains]
        sub_intervals.sort(key=lambda x: x[0])

        remaining_intervals: List[Tuple[float, float]] = []
        current_boundary = main_min  # Tracks where the next free interval could begin

        for sub_min, sub_max in sub_intervals:
            # Skip intervals entirely outside the parent range
            if sub_max < main_min or sub_min > main_max:
                continue

            # Any gap between the current boundary and this blocker is free
            gap_start = max(current_boundary, main_min)
            gap_end   = min(sub_min, main_max)
            if gap_start < gap_end:
                remaining_intervals.append((gap_start, gap_end))

            # Advance the boundary past this blocker
            current_boundary = max(current_boundary, min(sub_max, main_max))

        # Any space after the last blocker up to the parent boundary is also free
        if current_boundary < main_max:
            remaining_intervals.append((current_boundary, main_max))

        return remaining_intervals
