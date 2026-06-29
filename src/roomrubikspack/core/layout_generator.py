"""
roomrubikspack/core/layout_generator.py

This module contains the `LayoutGenerator` class which is responsible for the
low-level geometry math of placing rooms. It reads the BFS placement order and
iteratively adds each room to the floorplan.

For each new room, it:
1. Identifies the "parent" room it should attach to based on the adjacency graph.
2. Determines an initial placement point (often randomized to explore variants).
3. Utilizes `place_child.py` to iteratively slide the new room along the edges
   of existing rooms to resolve overlaps while preserving the required adjacency.
"""
from typing import List, Dict, Any, Optional
import math
import copy
import random

from ..utils.geometry import r1
from .place_child import PlaceChild
from .domain_subtractor import DomainSubtractor
from ..utils.correction_utils import get_corrected_variants
from .adjuster import Adjuster
from .attached_room_placer import AttachedRoomPlacer
from ..utils.graph_utils import get_bfs_order

# FindClashingDomains class:
# Computes the free available area ("domain") next to a parent room where a child room can be placed,
# by finding and subtracting overlapping domains from other rooms.
class FindClashingDomains:
    def __init__(self, parent: List[float], child: List[float], input_domains: List[List[float]], side: str, overlap_distance: float = 1.0):
        self.parent = parent
        self.child = child
        self.input_domains = input_domains
        self.side = side
        self.overlap_distance = overlap_distance
        self.a_domain = None

    def available_domain(self):
        child_length = self.child[1] - self.child[0]
        child_width = self.child[3] - self.child[2]
        overlap = self.overlap_distance
        # Available domain: parent face ± (child_side - min_overlap) on the open axis.
        # Formula: side_of_parent + (child_side_length - overlap) on each side.
        if self.side == "T":
            a_d = [
                self.parent[0] - (child_length - overlap),
                self.parent[1] + (child_length - overlap),
                self.parent[3],
                self.parent[3] + child_width
            ]
        elif self.side == "B":
            a_d = [
                self.parent[0] - (child_length - overlap),
                self.parent[1] + (child_length - overlap),
                self.parent[2] - child_width,
                self.parent[2]
            ]
        elif self.side == "L":
            a_d = [
                self.parent[0] - child_length,
                self.parent[0],
                self.parent[2] - (child_width - overlap),
                self.parent[3] + (child_width - overlap)
            ]
        elif self.side == "R":
            a_d = [
                self.parent[1],
                self.parent[1] + child_length,
                self.parent[2] - (child_width - overlap),
                self.parent[3] + (child_width - overlap)
            ]
        else:
            a_d = [0, 0, 0, 0]
        self.a_domain = a_d

    def get_clashing_domains(self):
        subdomains = []
        self.available_domain()
        a_domain = self.a_domain
        for domain in self.input_domains:
            if self.is_within_area_domain(a_domain, domain):
                subdomains.append(domain)
        return subdomains, a_domain

    @staticmethod
    def is_within_area_domain(a_domain: List[float], domain: List[float]) -> bool:
        epsilon = 0.01
        x_overlap = max(a_domain[0], domain[0]) + epsilon < min(a_domain[1], domain[1])
        y_overlap = max(a_domain[2], domain[2]) + epsilon < min(a_domain[3], domain[3])
        return x_overlap and y_overlap

# LayoutGenerator class:
# The core algorithm that processes rooms, builds a BFS order based on connections,
# and attempts to place them one by one without overlaps.
class LayoutGenerator:
    def __init__(self, gridsize: float = 0.5, dim_gen: Optional[Any] = None):
        self.gridsize = gridsize
        self.min_gap = 1.0
        self.dim_gen = dim_gen

    def _has_strict_overlap(self, pnts: List[float], placed_domains: List[List[float]]) -> bool:
        epsilon = 0.05
        for d in placed_domains:
            x_overlap = pnts[0] + epsilon < d[1] and pnts[1] - epsilon > d[0]
            y_overlap = pnts[2] + epsilon < d[3] and pnts[3] - epsilon > d[2]
            if x_overlap and y_overlap:
                return True
        return False

    def generate_layout(self, rooms: List[Any], connections: List[Any], start_room_id: str, options: Dict[str, Any] = None) -> Optional[List[Any]]:
        if options is None: options = {}
        location_variation = options.get("locationVariation", 0)
        gap_snap = options.get("gapSnap", 0)
        randomize_parents = options.get("randomizeParents", False)

        if not rooms or not start_room_id:
            return None

        main_rooms = []
        attached_rooms = []
        for r in rooms:
            r_copy = copy.copy(r)
            if r_copy.w is not None:
                r_copy.w = max(r_copy.w, 1.2)
            if r_copy.h is not None:
                r_copy.h = max(r_copy.h, 1.2)
            if not getattr(r, 'attachedSpace', False) and not getattr(r, 'attached', False):
                main_rooms.append(r_copy)
            else:
                r_copy.attached = True
                attached_rooms.append(r_copy)

        if not main_rooms:
            return None

        start_id = start_room_id
        if any(r.id == start_room_id for r in attached_rooms):
            start_id = main_rooms[0].id

        main_room_ids = [r.id for r in main_rooms]
        edges = []
        for c in connections:
            if c.roomA in main_room_ids and c.roomB in main_room_ids:
                edges.append([c.roomA, c.roomB])

        bfs_order = get_bfs_order(main_room_ids, connections, start_id, randomize_parents)
        if not bfs_order:
            return None

        layout_rooms = []
        placed_domains = []

        start_room = next((r for r in main_rooms if r.id == bfs_order[0]), None)
        if not start_room: return None

        start_children = [child for child in attached_rooms if any(
            (c.roomA == start_room.id and c.roomB == child.id) or (c.roomA == child.id and c.roomB == start_room.id)
            for c in connections
        )]
        
        start_variants = []
        if getattr(self, 'dim_gen', None) and getattr(start_room, 'area', None):
            possible_dims = self.dim_gen.get_possible_dimensions(start_room.area)
            if possible_dims:
                base_s = [[p["w"], p["h"]] for p in possible_dims]
                for bv in base_s:
                    start_variants.extend(get_corrected_variants(bv[0], bv[1], start_children))
        
        if not start_variants:
            start_variants = get_corrected_variants(start_room.w, start_room.h, start_children)
            
        if randomize_parents:
            svw, svh = random.choice(start_variants)
        else:
            svw, svh = start_variants[0]

        start_domain = self._create_initial_domain(start_room, location_variation, svw, svh)
        start_room.w = svw
        start_room.h = svh
        start_room.domain = start_domain
        layout_rooms.append(start_room)
        placed_domains.append(start_domain)

        placed_set = {start_room.id}

        for i in range(1, len(bfs_order)):
            current_id = bfs_order[i]
            current_room = next((r for r in main_rooms if r.id == current_id), None)
            if not current_room: continue

            neighbors = [e[1] if e[0] == current_id else e[0] for e in edges if e[0] == current_id or e[1] == current_id]

            valid_parents = [n for n in neighbors if n in placed_set]
            if not valid_parents: continue

            parent_id = None
            if randomize_parents and len(valid_parents) > 1:
                parent_id = random.choice(valid_parents)
            else:
                parent_id = valid_parents[0]

            parent_room = next((r for r in layout_rooms if r.id == parent_id), None)
            if not parent_room: continue
            parent_dom = parent_room.domain

            children = [child for child in attached_rooms if any(
                (c.roomA == current_id and c.roomB == child.id) or (c.roomA == child.id and c.roomB == current_id)
                for c in connections
            )]
            
            if getattr(self, 'dim_gen', None) and getattr(current_room, 'area', None):
                possible_dims = self.dim_gen.get_possible_dimensions(current_room.area)
                base_variants = [[p["w"], p["h"]] for p in possible_dims] if possible_dims else [[current_room.w, current_room.h]]
                raw_variants = []
                for bv in base_variants:
                    raw_variants.extend(get_corrected_variants(bv[0], bv[1], children))
                
                variants = []
                seen = set()
                for v in raw_variants:
                    sig = f"{v[0]:.2f},{v[1]:.2f}"
                    if sig not in seen:
                        seen.add(sig)
                        variants.append(v)
            else:
                variants = get_corrected_variants(current_room.w, current_room.h, children)

            best_domain = None
            best_dist = float('inf')
            best_vw = current_room.w
            best_vh = current_room.h

            overlap_distance = 1.2  # Minimum shared wall length between parent and child
            input_domains = [dom for dom in placed_domains if dom != parent_dom]

            # Domains of rooms directly connected to current_room (may touch it, exempt from gap check)
            neighbor_domains = []
            for n_id in neighbors:
                nr = next((r for r in layout_rooms if r.id == n_id), None)
                if nr and hasattr(nr, 'domain'):
                    neighbor_domains.append(nr.domain)

            for vw, vh in variants:
                child_dom_init = self._create_initial_domain(current_room, location_variation, vw, vh)
                sides = ['T', 'B', 'L', 'R']
                if randomize_parents:
                    random.shuffle(sides)

                for label in sides:
                    try:
                        finder = FindClashingDomains(parent_dom, child_dom_init, input_domains, label, overlap_distance)
                        clashing_domains, a_domain = finder.get_clashing_domains()
                        subtractor = DomainSubtractor(a_domain, clashing_domains)
                        axis = 0 if label in ('T', 'B') else 1
                        available_intervals = subtractor.subtract(axis)

                        ax = []
                        for start, end in available_intervals:
                            parent_start = parent_dom[0] if label in ('T', 'B') else parent_dom[2]
                            parent_end = parent_dom[1] if label in ('T', 'B') else parent_dom[3]
                            if start < parent_end and end > parent_start:
                                ax.append([start, end])

                        if ax:
                            area = vw * vh
                            placechild = PlaceChild(parent_dom, child_dom_init, overlap_distance, input_domains, a_domain, ax, label, area, self.gridsize)
                            pnts_list = placechild.place_child()

                            if pnts_list:
                                pnts = pnts_list[0]["fullDomain"]
                                if not self._has_strict_overlap(pnts, placed_domains):
                                    # Verify child actually touches parent (min 1.2m shared wall)
                                    if not self._shares_wall(pnts, parent_dom, overlap_distance):
                                        continue  # Reject floating placements
                                    # Verify minimum air gap from non-parent rooms is respected.
                                    # Exempt rooms that are directly connected to current_room.
                                    if gap_snap > 0 and self._has_gap_violation(
                                            pnts, parent_dom, placed_domains, gap_snap, neighbor_domains):
                                        continue  # Reject placements too close to non-connected rooms
                                    dist = self._distance_to_initial(pnts, current_room)
                                    if randomize_parents:
                                        dist *= (0.6 + random.random() * 0.8)
                                    if dist < best_dist:
                                        best_dist = dist
                                        best_domain = pnts
                                        best_vw = vw
                                        best_vh = vh
                    except Exception as e:
                        pass

            if best_domain:
                current_room.w = best_vw
                current_room.h = best_vh
                current_room.domain = best_domain
                layout_rooms.append(current_room)
                placed_domains.append(best_domain)
                placed_set.add(current_id)

        if gap_snap > 0:
            Adjuster.adjust(layout_rooms, connections, gap_snap)

        AttachedRoomPlacer.place_attached_rooms(attached_rooms, layout_rooms, connections, placed_domains, gap_snap)

        for r in layout_rooms:
            r.x = r.domain[0]
            r.y = r.domain[2]
            r.w = r.domain[1] - r.domain[0]
            r.h = r.domain[3] - r.domain[2]

        return layout_rooms

    def _shares_wall(self, child_dom: List[float], parent_dom: List[float], min_overlap: float) -> bool:
        """
        Checks that child_dom shares a wall with parent_dom of at least min_overlap length.
        Epsilon is generous (0.15) to handle r1() rounding artifacts where touching rooms
        may show a ~0.1m numerical gap.
        """
        epsilon = 0.15
        touches_x_right = abs(child_dom[0] - parent_dom[1]) <= epsilon
        touches_x_left  = abs(child_dom[1] - parent_dom[0]) <= epsilon
        touches_y_top   = abs(child_dom[2] - parent_dom[3]) <= epsilon
        touches_y_bot   = abs(child_dom[3] - parent_dom[2]) <= epsilon

        if touches_x_right or touches_x_left:
            y_overlap = min(child_dom[3], parent_dom[3]) - max(child_dom[2], parent_dom[2])
            return y_overlap >= min_overlap
        if touches_y_top or touches_y_bot:
            x_overlap = min(child_dom[1], parent_dom[1]) - max(child_dom[0], parent_dom[0])
            return x_overlap >= min_overlap
        return False

    def _has_gap_violation(self, child_dom: List[float], parent_dom: List[float], all_domains: List[List[float]], min_gap: float, exempt_domains: List[List[float]] = None) -> bool:
        """
        Returns True if child_dom ends up closer than min_gap to any non-connected domain.
        Skips parent_dom and any domain in exempt_domains (directly connected rooms).
        """
        epsilon = 0.05
        exempt = set(id(d) for d in (exempt_domains or []))
        exempt.add(id(parent_dom))
        for d in all_domains:
            if id(d) in exempt:
                continue
            # Y span shared -> check horizontal gap
            y_share = min(child_dom[3], d[3]) - max(child_dom[2], d[2])
            if y_share > 0.1:
                gap_x_ab = d[0] - child_dom[1]
                gap_x_ba = child_dom[0] - d[1]
                if 0 < gap_x_ab < min_gap - epsilon:
                    return True
                if 0 < gap_x_ba < min_gap - epsilon:
                    return True
            # X span shared -> check vertical gap
            x_share = min(child_dom[1], d[1]) - max(child_dom[0], d[0])
            if x_share > 0.1:
                gap_y_ab = d[2] - child_dom[3]
                gap_y_ba = child_dom[2] - d[3]
                if 0 < gap_y_ab < min_gap - epsilon:
                    return True
                if 0 < gap_y_ba < min_gap - epsilon:
                    return True
        return False

    def _create_initial_domain(self, room: Any, location_variation: float = 0, override_w: float = None, override_h: float = None) -> List[float]:
        w = override_w if override_w is not None else room.w
        h = override_h if override_h is not None else room.h
        cx = getattr(room, 'x', 0) + w / 2.0
        cy = getattr(room, 'y', 0) + h / 2.0

        if location_variation > 0:
            cx += (random.random() * 2 - 1) * location_variation
            cy += (random.random() * 2 - 1) * location_variation

        return [r1(cx - w / 2.0), r1(cx + w / 2.0), r1(cy - h / 2.0), r1(cy + h / 2.0)]

    def _distance_to_initial(self, domain: List[float], room: Any) -> float:
        cx = (domain[0] + domain[1]) / 2.0
        cy = (domain[2] + domain[3]) / 2.0
        initial_cx = getattr(room, 'x', 0) + getattr(room, 'w', 0) / 2.0
        initial_cy = getattr(room, 'y', 0) + getattr(room, 'h', 0) / 2.0
        return math.hypot(cx - initial_cx, cy - initial_cy)
