"""
roomrubikspack/core/place_child.py

This module provides the collision-resolution logic for the LayoutGenerator.
It contains functions (`adjust_right`, `adjust_bottom`, `adjust_left`, `adjust_top`) 
that attempt to resolve overlaps by shifting a newly placed room (the "child") 
along the outer boundary of its parent room.

If shifting in one direction doesn't resolve the overlap (e.g. it hits a third room),
it tries other orthogonal directions. It is highly iterative and acts as the
primary spatial packer for the floorplan.
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from ..utils.geometry import r1

class PlaceChild:
    def __init__(self, parent: List[float], child: List[float], overlap_distance: float, 
                 input_domains: List[List[float]], a_domain: List[float], 
                 remaining_intervals: List[Tuple[float, float]], side: str, 
                 area: float, gridsize: Union[float, List[float]]):
        self.parent = parent
        self.child = child
        self.overlap_distance = overlap_distance
        self.input_domains = input_domains
        self.a_domain = a_domain
        self.remaining_intervals = remaining_intervals
        self.side = side
        self.area = area
        self.gridsize = gridsize

    def _calculate_breadth(self, area: float, length: float, gridsize: Union[float, List[float]]) -> float:
        valid_length = 1 if length == 0 else abs(length)
        raw_breadth = area / valid_length
        breadth = raw_breadth

        if isinstance(gridsize, list) and len(gridsize) > 0:
            breadth = min(gridsize, key=lambda curr: abs(curr - raw_breadth))
        else:
            gs = gridsize if isinstance(gridsize, (int, float)) else 1.0
            rounded = round(raw_breadth / gs) * gs
            breadth = rounded if rounded > 0 else raw_breadth

        return breadth

    def adjust_top(self, side: str, area: float, gridsize: Union[float, List[float]], parent: List[float], min_x: float, max_x: float, input_domains: List[List[float]]):
        length = abs(max_x - min_x)
        breadth = self._calculate_breadth(area, length, gridsize)
        original_breadth = area / length if length > 0 else breadth
        snap_threshold = original_breadth * 0.10
        parent_y1 = r1(parent[3])
        parent_y2 = r1(parent_y1 + breadth)

        if input_domains:
            ys = [y for dom in input_domains for y in (dom[2], dom[3]) if y > parent_y1]
            if ys:
                mys = [dom[2] for dom in input_domains if not (dom[1] <= min_x or dom[0] >= max_x)]
                max_ys = min(mys) if mys else None
                r_ys = list(set(y for y in ys if y <= max_ys)) if max_ys is not None else list(set(ys))
                if r_ys:
                    r_parent_y2 = min(r_ys, key=lambda curr: abs(curr - parent_y2))
                    if abs(parent_y2 - r_parent_y2) < snap_threshold:
                        parent_y2 = r1(r_parent_y2)
        return [parent_y1, parent_y2]

    def adjust_bottom(self, side: str, area: float, gridsize: Union[float, List[float]], parent: List[float], min_x: float, max_x: float, input_domains: List[List[float]]):
        length = abs(max_x - min_x)
        breadth = self._calculate_breadth(area, length, gridsize)
        original_breadth = area / length if length > 0 else breadth
        snap_threshold = original_breadth * 0.10
        parent_y2 = r1(parent[2])
        parent_y1 = r1(parent_y2 - breadth)

        if input_domains:
            ys = [y for dom in input_domains for y in (dom[2], dom[3]) if y < parent_y2]
            if ys:
                mys = [dom[3] for dom in input_domains if not (dom[1] <= min_x or dom[0] >= max_x)]
                max_ys = max(mys) if mys else None
                r_ys = list(set(y for y in ys if y >= max_ys)) if max_ys is not None else list(set(ys))
                if r_ys:
                    r_parent_y1 = min(r_ys, key=lambda curr: abs(curr - parent_y1))
                    if abs(parent_y1 - r_parent_y1) < snap_threshold:
                        parent_y1 = r1(r_parent_y1)
        return [parent_y1, parent_y2]

    def adjust_left(self, side: str, area: float, gridsize: Union[float, List[float]], parent: List[float], min_y: float, max_y: float, input_domains: List[List[float]]):
        length = abs(max_y - min_y)
        breadth = self._calculate_breadth(area, length, gridsize)
        original_breadth = area / length if length > 0 else breadth
        snap_threshold = original_breadth * 0.10
        parent_x2 = r1(parent[0])
        parent_x1 = r1(parent_x2 - breadth)

        if input_domains:
            xs = [x for dom in input_domains for x in (dom[0], dom[1]) if x < parent_x2]
            if xs:
                mys = [dom[1] for dom in input_domains if not (dom[3] <= min_y or dom[2] >= max_y)]
                max_xs = max(mys) if mys else None
                r_xs = list(set(x for x in xs if x >= max_xs)) if max_xs is not None else list(set(xs))
                if r_xs:
                    r_parent_x1 = min(r_xs, key=lambda curr: abs(curr - parent_x1))
                    if abs(parent_x1 - r_parent_x1) < snap_threshold:
                        parent_x1 = r1(r_parent_x1)
        return [parent_x1, parent_x2]

    def adjust_right(self, side: str, area: float, gridsize: Union[float, List[float]], parent: List[float], min_y: float, max_y: float, input_domains: List[List[float]]):
        length = abs(max_y - min_y)
        breadth = self._calculate_breadth(area, length, gridsize)
        original_breadth = area / length if length > 0 else breadth
        snap_threshold = original_breadth * 0.10
        parent_x1 = r1(parent[1])
        parent_x2 = r1(parent_x1 + breadth)

        if input_domains:
            xs = [x for dom in input_domains for x in (dom[0], dom[1]) if x > parent_x1]
            if xs:
                mys = [dom[0] for dom in input_domains if not (dom[3] <= min_y or dom[2] >= max_y)]
                min_xs = min(mys) if mys else None
                r_xs = list(set(x for x in xs if x <= min_xs)) if min_xs is not None else list(set(xs))
                if r_xs:
                    r_parent_x2 = min(r_xs, key=lambda curr: abs(curr - parent_x2))
                    if abs(parent_x2 - r_parent_x2) < snap_threshold:
                        parent_x2 = r1(r_parent_x2)
        return [parent_x1, parent_x2]

    def adjust_right(child: 'Room', parent: 'Room', placed: List['Room'], allow_overlap: bool = False, min_overlap: float = 1.0) -> bool:
        """
        Attempts to place the child room to the right of the parent room.
        It slides the child vertically along the right edge of the parent, checking for
        collisions with any already `placed` rooms.
        """
        if parent.w is None or parent.h is None or child.w is None or child.h is None:
            return False
            
        # Start by assuming the child's left edge perfectly touches the parent's right edge
        best_x = parent.x + parent.w
        # Start sliding from the top of the parent down to the bottom
        start_y = parent.y + parent.h - child.h
        end_y = parent.y

        # We iterate vertically downwards in 0.1m increments
        current_y = start_y
        while current_y >= end_y:
            child.x = best_x
            child.y = current_y
            
            # Check if this current (x,y) position collides with any already placed rooms
            collision = False
            for p in placed:
                if _intersect(child, p):
                    collision = True
                    break
                    
            # If no collision, we found a valid position! We snap the Y coordinate and return.
            if not collision:
                child.y = r1(current_y)
                child.x = r1(best_x)
                return True
                
            current_y -= 0.1

        return False

    def clamp_domain(self, object_start: float, object_end: float, domain_start: float, domain_end: float, parent_start: float, parent_end: float):
        object_width = abs(object_end - object_start)
        domain_width = abs(domain_end - domain_start)
        min_gap = 1.2

        new_start = object_start
        new_end = object_end

        if object_width > domain_width:
            new_start = domain_start
            new_end = domain_end
            object_width = domain_width
        else:
            if new_start < domain_start:
                new_start = domain_start
                new_end = new_start + object_width
            elif new_end > domain_end:
                new_end = domain_end
                new_start = new_end - object_width

        overlap_start = max(new_start, parent_start)
        overlap_end = min(new_end, parent_end)

        if overlap_end - overlap_start < min_gap:
            if new_end <= parent_start + min_gap:
                new_end = min(domain_end, parent_start + min_gap)
                new_start = max(domain_start, new_end - object_width)
            elif new_start >= parent_end - min_gap:
                new_start = max(domain_start, parent_end - min_gap)
                new_end = min(domain_end, new_start + object_width)

        return [r1(new_start), r1(new_end)]

    def find_closest_interval(self) -> Optional[Tuple[float, float]]:
        if not self.remaining_intervals:
            return None
            
        child_span = self.child[1] - self.child[0]

        valid_intervals = [i for i in self.remaining_intervals if (i[1] - i[0]) >= child_span * 0.5]
        if not valid_intervals:
            valid_intervals = [i for i in self.remaining_intervals if (i[1] - i[0]) >= 1.0]
            
        if not valid_intervals:
            return None

        target_mid = (self.child[0] + self.child[1]) / 2.0
        return min(valid_intervals, key=lambda curr: abs((curr[0] + curr[1]) / 2.0 - target_mid))

    def place_child(self) -> List[Dict[str, Any]]:
        p_interval = self.find_closest_interval()
        if not p_interval:
            return []

        candidates = []

        res1 = self._generate_placement(list(p_interval))
        if res1: candidates.extend(res1)

        return candidates

    def _generate_placement(self, p_interval: List[float]) -> List[Dict[str, Any]]:
        result = None
        min_x = max_x = min_y = max_y = 0.0

        if self.side == 'T':
            child_w = self.child[1] - self.child[0]
            bounds = self.clamp_domain(self.child[0], self.child[0] + child_w, p_interval[0], p_interval[1], self.parent[0], self.parent[1])
            min_x, max_x = bounds
            y_bounds = self.adjust_top(self.side, self.area, self.gridsize, self.parent, min_x, max_x, self.input_domains)
            min_y, max_y = y_bounds
            result = [min_x, max_x, min_y, max_y]
        elif self.side == 'B':
            child_w = self.child[1] - self.child[0]
            bounds = self.clamp_domain(self.child[0], self.child[0] + child_w, p_interval[0], p_interval[1], self.parent[0], self.parent[1])
            min_x, max_x = bounds
            y_bounds = self.adjust_bottom(self.side, self.area, self.gridsize, self.parent, min_x, max_x, self.input_domains)
            min_y, max_y = y_bounds
            result = [min_x, max_x, min_y, max_y]
        elif self.side == 'L':
            child_h = self.child[3] - self.child[2]
            bounds = self.clamp_domain(self.child[2], self.child[2] + child_h, p_interval[0], p_interval[1], self.parent[2], self.parent[3])
            min_y, max_y = bounds
            x_bounds = self.adjust_left(self.side, self.area, self.gridsize, self.parent, min_y, max_y, self.input_domains)
            min_x, max_x = x_bounds
            result = [min_x, max_x, min_y, max_y]
        elif self.side == 'R':
            child_h = self.child[3] - self.child[2]
            bounds = self.clamp_domain(self.child[2], self.child[2] + child_h, p_interval[0], p_interval[1], self.parent[2], self.parent[3])
            min_y, max_y = bounds
            x_bounds = self.adjust_right(self.side, self.area, self.gridsize, self.parent, min_y, max_y, self.input_domains)
            min_x, max_x = x_bounds
            result = [min_x, max_x, min_y, max_y]

        if not result:
            return []
            
        result = [r1(x) for x in result]
        min_x, max_x, min_y, max_y = result

        candidates = []

        candidates.append({
            "fullDomain": result,
            "roomDomain": result,
            "side": self.side
        })

        return candidates
