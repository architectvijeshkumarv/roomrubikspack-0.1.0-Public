"""
utils/collision.py

Collision detection, resolution, and domain-overlap utilities.

Responsibilities:
  - resolve_collisions      : iteratively push apart overlapping rooms (AABB)
  - snap_to_grid            : quantise room positions to a grid
  - FindClashingDomains     : calculate which already-placed domains overlap with
                              the candidate placement region for a new room
"""

from typing import List, Tuple, Optional
from ..types import Room

# Type alias: a rectangular domain [min_x, max_x, min_y, max_y]
Domain = Tuple[float, float, float, float]


def resolve_collisions(rooms: List[Room], allowed_space_gap: float, iterations: int = 50) -> List[Room]:
    """
    Iteratively resolves AABB (Axis-Aligned Bounding Box) collisions between rooms.
    For each overlapping pair it pushes the rooms apart along the axis of smallest overlap.

    Args:
        rooms             : list of Room objects (modified in-place)
        allowed_space_gap : minimum required gap between rooms (metres)
        iterations        : maximum resolution passes; stops early if no collisions remain
    """
    resolved_rooms = list(rooms)

    for _ in range(iterations):
        has_collisions = False

        for i in range(len(resolved_rooms)):
            for j in range(i + 1, len(resolved_rooms)):
                roomA = resolved_rooms[i]
                roomB = resolved_rooms[j]

                # Extract AABB edges for each room
                aLeft = roomA.x;           aRight = roomA.x + (roomA.w or 0)
                aTop  = roomA.y + (roomA.h or 0); aBottom = roomA.y
                bLeft = roomB.x;           bRight = roomB.x + (roomB.w or 0)
                bTop  = roomB.y + (roomB.h or 0); bBottom = roomB.y

                # Penetration depth (positive = overlapping with required gap)
                overlapX = min(aRight, bRight) - max(aLeft, bLeft) + allowed_space_gap
                overlapY = min(aTop, bTop)     - max(aBottom, bBottom) + allowed_space_gap

                if overlapX > 0 and overlapY > 0:
                    has_collisions = True

                    # Resolve along the axis with the smallest penetration (minimal displacement)
                    if overlapX < overlapY:
                        shift = overlapX / 2.0
                        # Push A left and B right (or vice versa based on relative position)
                        if aLeft < bLeft:
                            roomA.x -= shift
                            roomB.x += shift
                        else:
                            roomA.x += shift
                            roomB.x -= shift
                    else:
                        shift = overlapY / 2.0
                        if aBottom < bBottom:
                            roomA.y -= shift
                            roomB.y += shift
                        else:
                            roomA.y += shift
                            roomB.y -= shift

        if not has_collisions:
            break  # Early exit — all collisions resolved before hitting the iteration limit

    return resolved_rooms


def snap_to_grid(rooms: List[Room], grid_size: float = 0.5) -> List[Room]:
    """
    Snaps all room (x, y) positions to the nearest grid increment.
    This prevents sub-millimetre coordinate drift and ensures clean wall alignments.

    Args:
        rooms     : list of Room objects (modified in-place)
        grid_size : grid increment in metres (default 0.5m = 500mm)
    """
    for room in rooms:
        room.x = round(room.x / grid_size) * grid_size
        room.y = round(room.y / grid_size) * grid_size
    return rooms


class FindClashingDomains:
    """
    Determines which already-placed room domains geometrically clash with the
    candidate placement region ('available domain') for a new room being added
    to a specific side (T/B/L/R) of its parent room.

    The 'available domain' is the rectangular zone where the new room could
    theoretically sit relative to its parent given the required overlap distance.
    Any existing room whose domain intersects this zone is a 'clashing domain'.

    This is used by PlaceChild to determine the free intervals along the parent's
    wall where the new room can actually be placed.
    """

    def __init__(self, parent: Domain, child: Domain, input_domains: List[Domain],
                 side: str, overlap_distance: float = 1.0):
        """
        Args:
            parent           : domain of the parent room [min_x, max_x, min_y, max_y]
            child            : domain of the child room being placed
            input_domains    : domains of all already-placed rooms
            side             : which side of the parent to place on: 'T', 'B', 'L', 'R'
            overlap_distance : minimum required shared wall length (metres)
        """
        self.parent = parent
        self.child = child
        self.input_domains = input_domains
        self.side = side
        self.overlap_distance = overlap_distance
        self.a_domain: Optional[Domain] = None  # Computed in available_domain()

    def available_domain(self):
        """
        Computes the rectangular zone ('available domain') where the child room can be placed.
        The zone extends beyond the parent on the specified side, accounting for overlap.
        Result is stored in self.a_domain.
        """
        child_length = self.child[1] - self.child[0]  # Child width (X span)
        child_width  = self.child[3] - self.child[2]  # Child height (Y span)
        overlap = self.overlap_distance

        if self.side == "T":   # Place child above parent
            a_d = (
                self.parent[0] - (child_length - overlap),  # Leftmost valid X start
                self.parent[1] + (child_length - overlap),  # Rightmost valid X end
                self.parent[3],                              # Y starts at top of parent
                self.parent[3] + child_width                # Y ends one child-height above
            )
        elif self.side == "B": # Place child below parent
            a_d = (
                self.parent[0] - (child_length - overlap),
                self.parent[1] + (child_length - overlap),
                self.parent[2] - child_width,               # Y ends at bottom of parent
                self.parent[2]
            )
        elif self.side == "L": # Place child to the left of parent
            a_d = (
                self.parent[0] - child_length,              # X starts one child-width left
                self.parent[0],
                self.parent[2] - (child_width - overlap),
                self.parent[3] + (child_width - overlap)
            )
        elif self.side == "R": # Place child to the right of parent
            a_d = (
                self.parent[1],
                self.parent[1] + child_length,              # X ends one child-width right
                self.parent[2] - (child_width - overlap),
                self.parent[3] + (child_width - overlap)
            )
        else:
            a_d = (0.0, 0.0, 0.0, 0.0)

        self.a_domain = a_d

    def clashing_domains(self) -> Tuple[List[Domain], Domain]:
        """
        Returns all placed domains that overlap with the available domain,
        plus the available domain itself (for downstream subtraction).
        """
        subdomains: List[Domain] = []
        self.available_domain()
        a_domain = self.a_domain
        if a_domain is not None:
            for domain in self.input_domains:
                if self.is_within_area_domain(a_domain, domain):
                    subdomains.append(domain)
        return subdomains, a_domain

    @staticmethod
    def is_within_area_domain(a_domain: Domain, domain: Domain) -> bool:
        """
        Returns True if 'domain' overlaps (or touches) 'a_domain' in both X and Y.
        Uses ≤ comparison (inclusive) so touching edges count as overlapping.
        """
        x_overlap = max(a_domain[0], domain[0]) <= min(a_domain[1], domain[1])
        y_overlap = max(a_domain[2], domain[2]) <= min(a_domain[3], domain[3])
        return x_overlap and y_overlap
