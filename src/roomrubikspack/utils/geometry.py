"""
roomrubikspack/utils/geometry.py

A library of low-level 2D geometric functions and helpers used heavily
by the LayoutGenerator and place_child collision resolution engine.

It includes functions for checking rectangle intersections, calculating overlaps,
determining relative orientation (left/right/top/bottom), and snapping coordinates
to nearest edges.
"""
from typing import List, Tuple, Dict
from ..types import Room

def r1(v: float) -> float:
    return round(v * 10) / 10.0

def has_strict_overlap(pnts: List[float], placed_domains: List[List[float]]) -> bool:
    # pnts: [min_x, max_x, min_y, max_y]
    epsilon = 0.05
    for d in placed_domains:
        x_overlap = (pnts[0] + epsilon < d[1]) and (pnts[1] - epsilon > d[0])
        y_overlap = (pnts[2] + epsilon < d[3]) and (pnts[3] - epsilon > d[2])
        if x_overlap and y_overlap:
            return True
    return False

def get_corrected_variants(parent_w: float, parent_h: float, children: List[Room]) -> List[Tuple[float, float]]:
    if not children:
        return [(parent_w, parent_h)]

    variants: List[Tuple[float, float]] = []
    total_child_area = sum([(c.w or 0) * (c.h or 0) for c in children])
    required_parent_area = parent_w * parent_h
    target_total_area = required_parent_area + total_child_area

    max_child_w = max([(c.w or 0) for c in children]) if children else 0
    max_child_h = max([(c.h or 0) for c in children]) if children else 0

    # Strategy A: Expand Width (X)
    children_sorted_by_h = sorted(children, key=lambda c: (c.h or 0), reverse=True)
    w_strip = 0.0
    temp_children = list(children_sorted_by_h)

    while temp_children:
        col_max_w = 0.0
        col_used_h = 0.0
        remaining_after_col = []
        for child in temp_children:
            if col_used_h + (child.h or 0) <= parent_h:
                col_used_h += (child.h or 0)
                col_max_w = max(col_max_w, (child.w or 0))
            else:
                remaining_after_col.append(child)
        
        if col_max_w == 0.0 and temp_children:
            col_max_w = temp_children[0].w or 0
            temp_children.pop(0)
        else:
            temp_children = remaining_after_col
        w_strip += col_max_w

    new_h_a = max(parent_h, max_child_h)
    new_w_a = target_total_area / new_h_a if new_h_a > 0 else 0
    new_w_a = max(new_w_a, w_strip + 1.2)

    variants.append((round(new_w_a, 2), round(new_h_a, 2)))

    # Strategy B: Expand Height (Y)
    children_sorted_by_w = sorted(children, key=lambda c: (c.w or 0), reverse=True)
    h_strip = 0.0
    temp_children = list(children_sorted_by_w)

    while temp_children:
        row_max_h = 0.0
        row_used_w = 0.0
        remaining_after_row = []
        for child in temp_children:
            if row_used_w + (child.w or 0) <= parent_w:
                row_used_w += (child.w or 0)
                row_max_h = max(row_max_h, (child.h or 0))
            else:
                remaining_after_row.append(child)
        
        if row_max_h == 0.0 and temp_children:
            row_max_h = temp_children[0].h or 0
            temp_children.pop(0)
        else:
            temp_children = remaining_after_row
        h_strip += row_max_h

    new_w_b = max(parent_w, max_child_w)
    new_h_b = target_total_area / new_w_b if new_w_b > 0 else 0
    new_h_b = max(new_h_b, h_strip + 1.2)

    variants.append((round(new_w_b, 2), round(new_h_b, 2)))

    # Unique variants
    unique = {}
    for v in variants:
        key = f"{v[0]},{v[1]}"
        if key not in unique:
            unique[key] = v
    return list(unique.values())

def find_external_segments(rooms: List[Room]) -> List[Dict[str, float]]:
    all_segments = []
    
    for r in rooms:
        x, y = r.x, r.y
        w, h = r.w or 0, r.h or 0
        all_segments.append({"x1": x, "y1": y + h, "x2": x + w, "y2": y + h})
        all_segments.append({"x1": x, "y1": y, "x2": x + w, "y2": y})
        all_segments.append({"x1": x, "y1": y, "x2": x, "y2": y + h})
        all_segments.append({"x1": x + w, "y1": y, "x2": x + w, "y2": y + h})

    external_segments = []
    epsilon = 0.001

    for seg in all_segments:
        is_shared = False
        mid_x = (seg["x1"] + seg["x2"]) / 2.0
        mid_y = (seg["y1"] + seg["y2"]) / 2.0
        
        # Check if midPoint is strictly inside another room
        for other in rooms:
            ox, oy = other.x, other.y
            ow, oh = other.w or 0, other.h or 0
            if (mid_x > ox + epsilon and mid_x < ox + ow - epsilon and
                mid_y > oy + epsilon and mid_y < oy + oh - epsilon):
                is_shared = True
                break
                
        if is_shared:
            continue
            
        overlap_count = 0
        for r in rooms:
            rx, ry = r.x, r.y
            rw, rh = r.w or 0, r.h or 0
            
            on_top = abs(mid_y - (ry + rh)) < epsilon and (mid_x >= rx - epsilon) and (mid_x <= rx + rw + epsilon)
            on_bottom = abs(mid_y - ry) < epsilon and (mid_x >= rx - epsilon) and (mid_x <= rx + rw + epsilon)
            on_left = abs(mid_x - rx) < epsilon and (mid_y >= ry - epsilon) and (mid_y <= ry + rh + epsilon)
            on_right = abs(mid_x - (rx + rw)) < epsilon and (mid_y >= ry - epsilon) and (mid_y <= ry + rh + epsilon)
            
            if on_top or on_bottom or on_left or on_right:
                overlap_count += 1
                
        if overlap_count > 1:
            is_vert = abs(seg["x1"] - seg["x2"]) < epsilon
            if is_vert:
                test_points = [{"x": mid_x - 0.05, "y": mid_y}, {"x": mid_x + 0.05, "y": mid_y}]
            else:
                test_points = [{"x": mid_x, "y": mid_y - 0.05}, {"x": mid_x, "y": mid_y + 0.05}]
                
            inside_count = 0
            for tp in test_points:
                for r in rooms:
                    rx, ry = r.x, r.y
                    rw, rh = r.w or 0, r.h or 0
                    if (tp["x"] > rx + epsilon and tp["x"] < rx + rw - epsilon and
                        tp["y"] > ry + epsilon and tp["y"] < ry + rh - epsilon):
                        inside_count += 1
                        break
            if inside_count > 1:
                is_shared = True

        if not is_shared:
            external_segments.append(seg)

    return external_segments
