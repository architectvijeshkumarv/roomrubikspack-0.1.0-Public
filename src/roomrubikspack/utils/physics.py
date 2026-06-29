"""
utils/physics.py

Simple force-directed physics simulation for initial room positioning.
This module is NOT used during the main GA layout generation (which uses geometric placement).
It can be used as a preprocessing step to get a rough initial layout before
passing rooms to the placement engine, or for research/experimentation.

The simulation applies:
  1. Spring forces  : attract connected rooms toward each other
  2. Repulsion forces: push overlapping or too-close rooms apart
"""

import math
from typing import List, Dict
from copy import deepcopy
from ..types import Room, Connection


def distance(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    """Returns the Euclidean distance between two 2D points {x, y}."""
    return math.sqrt(math.pow(p2["x"] - p1["x"], 2) + math.pow(p2["y"] - p1["y"], 2))


def normalize(v: Dict[str, float]) -> Dict[str, float]:
    """
    Returns the unit vector of a 2D vector {x, y}.
    Returns {0, 0} if the vector has zero length (degenerate case).
    """
    length = math.sqrt(v["x"] * v["x"] + v["y"] * v["y"])
    if length == 0:
        return {"x": 0.0, "y": 0.0}
    return {"x": v["x"] / length, "y": v["y"] / length}


def apply_forces(
    rooms: List[Room],
    connections: List[Connection],
    fixed_room_id: str,
    allowed_space_gap: float,
    use_corridors: bool,
    iterations: int = 100
) -> List[Room]:
    """
    Runs a force-directed simulation on the given rooms and returns
    updated Room objects with new (x, y) positions.

    The simulation works in two phases per iteration:
      Phase 1 — Spring forces: connected rooms attract each other
      Phase 2 — Repulsion forces: close/overlapping rooms push each other away

    Args:
        rooms            : input rooms (deep-copied internally, originals are not modified)
        connections      : adjacency graph edges (defines which rooms attract each other)
        fixed_room_id    : this room does not move (acts as the anchor/origin)
        allowed_space_gap: minimum gap between rooms in metres (affects rest length)
        use_corridors    : adds corridor width to the target spring rest length
        iterations       : number of simulation steps (more = more settled, slower)

    Returns:
        A new list of Room objects with updated x, y positions.
    """

    class SimulatedRoom:
        """Wraps a Room with velocity state for the physics simulation."""
        def __init__(self, room: Room):
            self.room = deepcopy(room)  # Deep copy so the original room is not mutated
            self.vx = 0.0              # X velocity component
            self.vy = 0.0              # Y velocity component

    # Build a map from room ID to its simulated wrapper for O(1) lookup
    sim_rooms_map = {r.id: SimulatedRoom(r) for r in rooms}
    sim_rooms = list(sim_rooms_map.values())

    # Physics constants
    k = 0.1         # Spring constant: higher = stronger attraction between connected rooms
    repulsion = 2.0 # Repulsion constant: higher = rooms push each other away more forcefully
    damping = 0.8   # Velocity damping (friction): lower = settles faster, may be less stable

    for _ in range(iterations):
        for i in range(len(sim_rooms)):
            simA = sim_rooms[i]

            # The fixed room (start space) is anchored — skip it
            if simA.room.id == fixed_room_id:
                continue

            fx = 0.0  # Net force in X direction for this room this step
            fy = 0.0  # Net force in Y direction for this room this step

            # --- Phase 1: Spring forces (attraction to connected rooms) ---
            connected_edges = [
                c for c in connections
                if c.roomA == simA.room.id or c.roomB == simA.room.id
            ]
            for edge in connected_edges:
                other_id = edge.roomB if edge.roomA == simA.room.id else edge.roomA
                if other_id not in sim_rooms_map:
                    continue
                simB = sim_rooms_map[other_id]

                dx = simB.room.x - simA.room.x
                dy = simB.room.y - simA.room.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist == 0:
                    dist = 0.1  # Avoid division by zero

                # Target rest distance: average dimension + gap + optional corridor width
                target_dist = (
                    (max(simA.room.w or 0, simA.room.h or 0) + max(simB.room.w or 0, simB.room.h or 0)) / 2.0
                    + allowed_space_gap
                    + (1.5 if use_corridors else 0.0)
                )

                # Hooke's law: force proportional to difference from rest length
                force = k * (dist - target_dist)
                dir_v = normalize({"x": dx, "y": dy})

                fx += dir_v["x"] * force
                fy += dir_v["y"] * force

            # --- Phase 2: Repulsion forces (push apart overlapping rooms) ---
            for j in range(len(sim_rooms)):
                if i == j:
                    continue  # Skip self
                simB = sim_rooms[j]

                dx = simA.room.x - simB.room.x
                dy = simA.room.y - simB.room.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist == 0:
                    dist = 0.1

                # Minimum allowed separation between room centres
                min_dist = ((simA.room.w or 0) + (simB.room.w or 0)) / 2.0 + allowed_space_gap
                if dist < min_dist:
                    # Repulsion force inversely proportional to proximity
                    force = repulsion * (min_dist - dist) / dist
                    fx += dx * force
                    fy += dy * force

            # Apply damping and accumulate velocity
            simA.vx = (simA.vx + fx) * damping
            simA.vy = (simA.vy + fy) * damping

        # Update positions after all forces are computed for this iteration
        for sim in sim_rooms:
            if sim.room.id != fixed_room_id:  # Never move the anchor room
                sim.room.x += sim.vx
                sim.room.y += sim.vy

    # Return the updated room list (positions reflect final simulation state)
    return [s.room for s in sim_rooms]
