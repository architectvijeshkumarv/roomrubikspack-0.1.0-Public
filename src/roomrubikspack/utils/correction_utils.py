from typing import List, Tuple, Any

def get_corrected_variants(parent_w: float, parent_h: float, children: List[Any]) -> List[Tuple[float, float]]:
    if not children:
        return [(parent_w, parent_h)]

    variants = []
    total_child_area = sum(c.w * c.h for c in children)
    required_parent_area = parent_w * parent_h
    target_total_area = required_parent_area + total_child_area

    max_child_w = max(c.w for c in children)
    max_child_h = max(c.h for c in children)

    # Strategy A: Expand Width (X)
    children_sorted_by_h = sorted(children, key=lambda c: c.h, reverse=True)
    w_strip = 0.0
    temp_children = list(children_sorted_by_h)
    
    while temp_children:
        col_max_w = 0.0
        col_used_h = 0.0
        remaining_after_col = []
        for child in temp_children:
            if col_used_h + child.h <= parent_h:
                col_used_h += child.h
                col_max_w = max(col_max_w, child.w)
            else:
                remaining_after_col.append(child)
                
        if col_max_w == 0.0:
            col_max_w = temp_children[0].w
            temp_children.pop(0)
        else:
            temp_children = remaining_after_col
        w_strip += col_max_w

    new_h_a = max(parent_h, max_child_h)
    new_w_a = target_total_area / new_h_a
    new_w_a = max(new_w_a, w_strip + 1.2)
    
    variants.append((round(new_w_a, 2), round(new_h_a, 2)))

    # Strategy B: Expand Height (Y)
    children_sorted_by_w = sorted(children, key=lambda c: c.w, reverse=True)
    h_strip = 0.0
    temp_children = list(children_sorted_by_w)
    
    while temp_children:
        row_max_h = 0.0
        row_used_w = 0.0
        remaining_after_row = []
        for child in temp_children:
            if row_used_w + child.w <= parent_w:
                row_used_w += child.w
                row_max_h = max(row_max_h, child.h)
            else:
                remaining_after_row.append(child)
                
        if row_max_h == 0.0:
            row_max_h = temp_children[0].h
            temp_children.pop(0)
        else:
            temp_children = remaining_after_row
        h_strip += row_max_h

    new_w_b = max(parent_w, max_child_w)
    new_h_b = target_total_area / new_w_b
    new_h_b = max(new_h_b, h_strip + 1.2)
    
    variants.append((round(new_w_b, 2), round(new_h_b, 2)))

    # Return unique variants
    unique = {}
    for v in variants:
        key = f"{v[0]},{v[1]}"
        unique[key] = v
        
    return list(unique.values())
