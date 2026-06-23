"""
utils/graph_utils.py

Graph utilities for the roomrubikspack layout engine.

Responsibilities:
- check_connectivity : verify all rooms form a single connected graph
- get_bfs_order      : produce a Breadth-First Search traversal order for placement
- check_planarity    : quick Euler formula check to warn about non-planar graphs
"""

import random
from typing import List, Dict, Optional, Set
from ..types import Connection


def check_connectivity(room_ids: List[str], connections: List[Connection]) -> bool:
    """
    Returns True if all rooms are reachable from the first room (i.e. the graph is connected).
    A disconnected graph would mean some rooms can never be placed adjacent to the start.
    """
    if len(room_ids) <= 1:
        return True  # A single room or empty list is trivially connected

    # Build adjacency list from the connection list
    adj: Dict[str, List[str]] = {r_id: [] for r_id in room_ids}
    for conn in connections:
        if conn.roomA in adj:
            adj[conn.roomA].append(conn.roomB)
        if conn.roomB in adj:
            adj[conn.roomB].append(conn.roomA)

    # Standard BFS from the first room
    visited: Set[str] = set()
    queue = [room_ids[0]]
    visited.add(room_ids[0])

    while queue:
        u = queue.pop(0)
        for v in adj.get(u, []):
            if v not in visited:
                visited.add(v)
                queue.append(v)

    # All rooms must be visited for the graph to be connected
    return len(visited) == len(room_ids)


def get_bfs_order(
    room_ids: List[str],
    connections: List[Connection],
    start_room_id: Optional[str] = None,
    shuffle_list: bool = False
) -> List[str]:
    """
    Returns the room IDs in Breadth-First Search order starting from start_room_id.
    This order is used by the layout generator to place rooms one-by-one, ensuring
    that each room's parent is already placed before the room itself is processed.

    Args:
        room_ids       : all room IDs to traverse
        connections    : adjacency edges between rooms
        start_room_id  : the room to begin traversal from (should be startSpace)
        shuffle_list   : if True, randomises neighbour order at each BFS step
                         (used by the GA to explore different layout topologies)
    """
    if not room_ids:
        return []

    # Build undirected adjacency list restricted to provided room_ids
    adj: Dict[str, List[str]] = {r_id: [] for r_id in room_ids}
    for conn in connections:
        if conn.roomA in adj:
            adj[conn.roomA].append(conn.roomB)
        if conn.roomB in adj:
            adj[conn.roomB].append(conn.roomA)

    order: List[str] = []
    visited: Set[str] = set()

    # Fall back to first room if start_room_id is not found
    start_id = start_room_id if (start_room_id and start_room_id in room_ids) else room_ids[0]

    queue = [start_id]
    visited.add(start_id)

    while queue:
        u = queue.pop(0)
        order.append(u)

        neighbors = list(adj.get(u, []))
        if shuffle_list:
            random.shuffle(neighbors)   # Random order = different layout exploration
        else:
            neighbors.sort()            # Deterministic order for reproducibility

        for v in neighbors:
            if v not in visited:
                visited.add(v)
                queue.append(v)

    # Handle disconnected components — append them after the main connected component
    for r_id in room_ids:
        if r_id not in visited:
            sub_queue = [r_id]
            visited.add(r_id)
            while sub_queue:
                u = sub_queue.pop(0)
                order.append(u)
                neighbors = list(adj.get(u, []))
                if shuffle_list:
                    random.shuffle(neighbors)
                else:
                    neighbors.sort()
                for v in neighbors:
                    if v not in visited:
                        visited.add(v)
                        sub_queue.append(v)

    return order


def check_planarity(room_ids: List[str], connections: List[Connection]) -> bool:
    """
    Quick necessary-condition check for graph planarity using Euler's formula.
    For a planar graph: E ≤ 3V − 6  (where V = vertices, E = edges).

    NOTE: This is a necessary but NOT sufficient condition. It will catch
    obvious non-planar cases but not all of them. Use as a warning only.

    Returns True if the graph MIGHT be planar, False if it is DEFINITELY non-planar.
    """
    v = len(room_ids)   # Number of vertices (rooms)
    e = len(connections)  # Number of edges (connections)

    if v <= 2:
        return True  # Any graph with ≤2 vertices is always planar

    # Euler's inequality: a planar graph cannot have more than 3V-6 edges
    if e > 3 * v - 6:
        return False  # Definitely non-planar

    return True  # Likely planar (not guaranteed)
