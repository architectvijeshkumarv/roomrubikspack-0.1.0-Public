from typing import List, Dict, Any, Optional, Tuple
from ..utils.geometry import r1
import math
import copy

class AttachedRoomPlacer:
    @staticmethod
    def place_attached_rooms(attached_rooms: List[Any], layout_rooms: List[Any], connections: List[Any], placed_domains: List[List[float]], _gap_snap: float) -> List[Any]:
        gap_snap = 1.2
        
        groups: Dict[str, List[Any]] = {}
        for r in attached_rooms:
            conn = next((c for c in connections if c.roomA == r.id or c.roomB == r.id), None)
            if not conn: continue
            parent_id = conn.roomB if conn.roomA == r.id else conn.roomA
            if parent_id not in groups:
                groups[parent_id] = []
            groups[parent_id].append(r)

        for parent_id, parent_children in groups.items():
            # Identify the parent room's geometry to attach the children to
            parent_layout = next((lr for lr in layout_rooms if lr.id == parent_id), None)
            if not parent_layout: continue

            best_config = AttachedRoomPlacer._find_best_config(parent_children, parent_layout, layout_rooms, connections, placed_domains)
            if best_config:
                for r in best_config:
                    layout_rooms.append(r)
                    placed_domains.append(r.domain)

        AttachedRoomPlacer._snap_attached_rooms(layout_rooms, connections, gap_snap)
        return layout_rooms

    @staticmethod
    def _find_best_config(children: List[Any], parent_layout: Any, layout_rooms: List[Any], connections: List[Any], placed_domains: List[List[float]]) -> Optional[List[Any]]:
        if not children: return None
        
        max_perms = 1000 if len(children) <= 4 else 10
        best_layout = None
        best_score = float('inf')
        
        num_orientations = 1 << len(children)
        orders = AttachedRoomPlacer._get_permutations(children)
        
        for order in orders:
            for i in range(num_orientations):
                config = [{"room": r, "swap": ((i >> idx) & 1) == 1} for idx, r in enumerate(order)]
                current_layout = AttachedRoomPlacer._try_placement(config, parent_layout, layout_rooms, connections, placed_domains)
                if current_layout:
                    score = AttachedRoomPlacer._score_layout(current_layout, parent_layout)
                    if score < best_score:
                        best_score = score
                        best_layout = current_layout
            if best_layout and len(orders) > max_perms:
                break
                
        return best_layout

    @staticmethod
    def _get_permutations(array: List[Any]) -> List[List[Any]]:
        if len(array) <= 1: return [array]
        if len(array) > 5: return [array]
        
        result = []
        for i in range(len(array)):
            char = array[i]
            remaining_chars = array[:i] + array[i+1:]
            for permutation in AttachedRoomPlacer._get_permutations(remaining_chars):
                result.append([char] + permutation)
        return result

    @staticmethod
    def _has_strict_overlap(pnts: List[float], domains: List[List[float]]) -> bool:
        epsilon = 0.05
        for d in domains:
            x_overlap = pnts[0] + epsilon < d[1] and pnts[1] - epsilon > d[0]
            y_overlap = pnts[2] + epsilon < d[3] and pnts[3] - epsilon > d[2]
            if x_overlap and y_overlap:
                return True
        return False

    @staticmethod
    def _try_placement(config: List[Dict[str, Any]], parent_layout: Any, layout_rooms: List[Any], connections: List[Any], placed_domains: List[List[float]]) -> Optional[List[Any]]:
        p_dom = parent_layout.domain
        max_l = p_dom[1] - p_dom[0]
        max_w = p_dom[3] - p_dom[2]
        internal_placed: List[List[float]] = []
        result: List[Any] = []
        
        for c_item in config:
            r = c_item["room"]
            swap = c_item["swap"]
            
            orientations = [[r.h, r.w], [r.w, r.h]] if swap else [[r.w, r.h], [r.h, r.w]]
            req_l, req_w = orientations[0]
            
            child_l = r1(min(req_l, max_l))
            child_w = r1(min(req_w, max_w))
            
            if child_l < 1.2: child_l = min(1.2, max_l)
            if child_w < 1.2: child_w = min(1.2, max_w)
            
            if abs(max_l - child_l) < 1.0 and max_l >= 1.2: child_l = max_l
            if abs(max_w - child_w) < 1.0 and max_w >= 1.2: child_w = max_w
            
            candidates = []
            matched_candidates = []
            
            for placed in internal_placed:
                # Right of placed
                if placed[1] + child_l <= p_dom[1]:
                    if placed[3] - child_w >= p_dom[2]: matched_candidates.append([placed[1], placed[1] + child_l, placed[3] - child_w, placed[3]])
                    if placed[2] + child_w <= p_dom[3]: matched_candidates.append([placed[1], placed[1] + child_l, placed[2], placed[2] + child_w])
                # Left of placed
                if placed[0] - child_l >= p_dom[0]:
                    if placed[3] - child_w >= p_dom[2]: matched_candidates.append([placed[0] - child_l, placed[0], placed[3] - child_w, placed[3]])
                    if placed[2] + child_w <= p_dom[3]: matched_candidates.append([placed[0] - child_l, placed[0], placed[2], placed[2] + child_w])
                # Top of placed
                if placed[3] + child_w <= p_dom[3]:
                    if placed[0] + child_l <= p_dom[1]: matched_candidates.append([placed[0], placed[0] + child_l, placed[3], placed[3] + child_w])
                    if placed[1] - child_l >= p_dom[0]: matched_candidates.append([placed[1] - child_l, placed[1], placed[3], placed[3] + child_w])
                # Bottom of placed
                if placed[2] - child_w >= p_dom[2]:
                    if placed[0] + child_l <= p_dom[1]: matched_candidates.append([placed[0], placed[0] + child_l, placed[2] - child_w, placed[2]])
                    if placed[1] - child_l >= p_dom[0]: matched_candidates.append([placed[1] - child_l, placed[1], placed[2] - child_w, placed[2]])
                    
            corner_candidates = [
                [p_dom[0], p_dom[0] + child_l, p_dom[3] - child_w, p_dom[3]],
                [p_dom[1] - child_l, p_dom[1], p_dom[3] - child_w, p_dom[3]],
                [p_dom[0], p_dom[0] + child_l, p_dom[2], p_dom[2] + child_w],
                [p_dom[1] - child_l, p_dom[1], p_dom[2], p_dom[2] + child_w]
            ]
            
            candidates.extend(matched_candidates)
            candidates.extend(corner_candidates)
            
            placed_domain = None
            for c in candidates:
                # Validate the candidate position does not strictly overlap with any already placed rooms
                if not AttachedRoomPlacer._has_strict_overlap(c, internal_placed):
                    placed_domain = [r1(c[0]), r1(c[1]), r1(c[2]), r1(c[3])]
                    break
                    
            if not placed_domain: return None
            
            new_r = copy.copy(r)
            new_r.domain = placed_domain
            result.append(new_r)
            internal_placed.append(placed_domain)
            
        return result

    @staticmethod
    def _score_layout(placed: List[Any], parent: Any) -> float:
        score = 0
        p_dom = parent.domain
        sides = ['top', 'bottom', 'left', 'right']
        
        for side in sides:
            side_rooms = []
            for r in placed:
                d = r.domain
                if side == 'top' and abs(d[3] - p_dom[3]) < 0.1: side_rooms.append(r)
                elif side == 'bottom' and abs(d[2] - p_dom[2]) < 0.1: side_rooms.append(r)
                elif side == 'left' and abs(d[0] - p_dom[0]) < 0.1: side_rooms.append(r)
                elif side == 'right' and abs(d[1] - p_dom[1]) < 0.1: side_rooms.append(r)
                
            if not side_rooms: continue
            
            depths = set()
            for r in side_rooms:
                d = r.domain
                depth = r1(d[3] - d[2] if side in ['top', 'bottom'] else d[1] - d[0])
                depths.add(f"{depth:.1f}")
                
            score += (len(depths) - 1) * 100
            
            for r in side_rooms:
                d = r.domain
                is_full_width = side in ['top', 'bottom'] and abs((d[1] - d[0]) - (p_dom[1] - p_dom[0])) < 0.1
                is_full_height = side in ['left', 'right'] and abs((d[3] - d[2]) - (p_dom[3] - p_dom[2])) < 0.1
                if is_full_width or is_full_height:
                    score -= 50
                    
            if side in ['top', 'bottom']:
                side_rooms.sort(key=lambda x: x.domain[0])
            else:
                side_rooms.sort(key=lambda x: x.domain[2])
                
            for i in range(len(side_rooms) - 1):
                d1 = side_rooms[i].domain
                d2 = side_rooms[i+1].domain
                gap = d2[0] - d1[1] if side in ['top', 'bottom'] else d2[2] - d1[3]
                if gap > 0.1: score += 50
                
        return score


    @staticmethod
    def _snap_attached_rooms(layout_rooms: List[Any], connections: List[Any], gap_snap: float):
        attached = [r for r in layout_rooms if getattr(r, 'attached', False)]
        if not attached: return
        
        groups: Dict[str, List[Any]] = {}
        for r in attached:
            conn = next((c for c in connections if c.roomA == r.id or c.roomB == r.id), None)
            if not conn: continue
            parent_id = conn.roomB if conn.roomA == r.id else conn.roomA
            if parent_id not in groups: groups[parent_id] = []
            groups[parent_id].append(r)
            
        for parent_id, children in groups.items():
            parent_room = next((r for r in layout_rooms if r.id == parent_id), None)
            if not parent_room: continue
            p_dom = parent_room.domain
            
            side_groups: Dict[str, List[Any]] = {'top': [], 'bottom': [], 'left': [], 'right': []}
            
            for r in children:
                d = r.domain
                if abs(d[3] - p_dom[3]) < 0.1: side_groups['top'].append(r)
                elif abs(d[2] - p_dom[2]) < 0.1: side_groups['bottom'].append(r)
                elif abs(d[0] - p_dom[0]) < 0.1: side_groups['left'].append(r)
                elif abs(d[1] - p_dom[1]) < 0.1: side_groups['right'].append(r)
                
            for side, side_children in side_groups.items():
                if not side_children: continue
                
                is_horizontal = side in ['top', 'bottom']
                if is_horizontal:
                    side_children.sort(key=lambda x: x.domain[0])
                else:
                    side_children.sort(key=lambda x: x.domain[2])
                    
                # 1. Gap Adjustment
                for r in side_children:
                    d = r.domain
                    if is_horizontal:
                        if 0.01 < abs(d[0] - p_dom[0]) <= gap_snap: d[0] = p_dom[0]
                        if 0.01 < abs(d[1] - p_dom[1]) <= gap_snap: d[1] = p_dom[1]
                    else:
                        if 0.01 < abs(d[2] - p_dom[2]) <= gap_snap: d[2] = p_dom[2]
                        if 0.01 < abs(d[3] - p_dom[3]) <= gap_snap: d[3] = p_dom[3]
                        
                for i in range(len(side_children) - 1):
                    dA = side_children[i].domain
                    dB = side_children[i+1].domain
                    gap = dB[0] - dA[1] if is_horizontal else dB[2] - dA[3]
                    if 0.01 < gap <= gap_snap:
                        mid = r1((dA[1 if is_horizontal else 3] + dB[0 if is_horizontal else 2]) / 2)
                        if is_horizontal:
                            dA[1] = mid
                            dB[0] = mid
                        else:
                            dA[3] = mid
                            dB[2] = mid
                            
                # 2. Uniform Depth Alignment
                total_area = 0.0
                total_span = 0.0
                for r in side_children:
                    total_area += r.w * r.h
                    d = r.domain
                    total_span += (d[1] - d[0]) if is_horizontal else (d[3] - d[2])
                    
                if total_span > 0.1:
                    target_depth = r1(total_area / total_span)
                    for r in side_children:
                        d = r.domain
                        if side == 'top': d[2] = r1(d[3] - target_depth)
                        elif side == 'bottom': d[3] = r1(d[2] + target_depth)
                        elif side == 'left': d[1] = r1(d[0] + target_depth)
                        elif side == 'right': d[0] = r1(d[1] - target_depth)
                        
            # 3. Pairwise Snapping Fallback
            for i in range(len(children)):
                for j in range(i + 1, len(children)):
                    rA = children[i]
                    rB = children[j]
                    dA = rA.domain
                    dB = rB.domain
                    areaA = rA.w * rA.h
                    
                    y_overlap = max(dA[2], dB[2]) < min(dA[3], dB[3]) - 0.1
                    if y_overlap:
                        gap1 = dB[0] - dA[1]
                        gap2 = dA[0] - dB[1]
                        if 0.01 < abs(gap1) <= gap_snap:
                            dA[1] = dB[0]
                            newW = dA[1] - dA[0]
                            if newW > 0.1:
                                newH = areaA / newW
                                if abs(dA[3] - p_dom[3]) < 0.1: dA[2] = r1(dA[3] - newH)
                                elif abs(dA[2] - p_dom[2]) < 0.1: dA[3] = r1(dA[2] + newH)
                        elif 0.01 < abs(gap2) <= gap_snap:
                            dA[0] = dB[1]
                            newW = dA[1] - dA[0]
                            if newW > 0.1:
                                newH = areaA / newW
                                if abs(dA[3] - p_dom[3]) < 0.1: dA[2] = r1(dA[3] - newH)
                                elif abs(dA[2] - p_dom[2]) < 0.1: dA[3] = r1(dA[2] + newH)

