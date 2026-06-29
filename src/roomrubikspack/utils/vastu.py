import math
"""
roomrubikspack/utils/vastu.py

Implements Vastu Shastra architectural compliance rules for the layout engine.
Vastu dictates specific cardinal directions (quadrants) for specific functional
rooms (e.g. Kitchens in SE/NW, Master Beds in SW).

This module provides two mechanisms that the Genetic Algorithm uses:
1. `preadjust_rooms_for_vastu`: Physically moves rooms into their ideal sectors
   before the layout generation starts, to bias the engine toward a good solution.
2. `evaluate_vastu_penalty`: Evaluates a generated layout and assigns heavy
   cost penalties to rooms that violate Vastu rules, so the GA weeds them out.
"""
from typing import List, Dict, Optional, Any
from copy import deepcopy
from ..types import Room

VASTU_RULES = [
    {
        "keywords": ['pooja', 'puja', 'prayer', 'temple', 'shrine'],
        "primarySector": 'NE',
        "description": 'Pooja room is best situated in the North-East corner for strong positive/spiritual energy.',
    },
    {
        "keywords": ['living', 'hall', 'lounge', 'family', 'parlor', 'salon'],
        "primarySector": 'NE',
        "description": 'Living room/Hall should be in the North-East or North for welcoming guest energy.',
    },
    {
        "keywords": ['kitchen', 'cooking', 'pantry'],
        "primarySector": 'SE',
        "description": 'Kitchen must be placed in the South-East corner, representing Agni (Lord of Fire).',
    },
    {
        "keywords": ['master', 'owner'],
        "primarySector": 'SW',
        "description": 'Master bedroom must be in the South-West corner to signify stability and leadership.',
    },
    {
        "keywords": ['bed', 'bedroom', 'guest bed', 'kids'],
        "primarySector": 'SW',
        "description": 'Bedrooms are ideal in the South-West or West to promote prosperity and peaceful sleep.',
    },
    {
        "keywords": ['bath', 'toilet', 'washroom', 'wc', 'powder', 'shower', 'restroom'],
        "primarySector": 'NW',
        "description": 'Toilets and bathrooms should be in the North-West, away from sacred zones.',
    },
    {
        "keywords": ['dining', 'din'],
        "primarySector": 'W',
        "description": 'Dining area is best placed in the West or East to support healthy digestion.',
    },
    {
        "keywords": ['study', 'office', 'library', 'work'],
        "primarySector": 'NE',
        "description": 'Study/Office room is best in the North-East, East or North to enhance concentration.',
    },
    {
        "keywords": ['entrance', 'foyer', 'lobby', 'entry', 'main door'],
        "primarySector": 'NE',
        "description": 'Main entrance foyer is best in the North-East, East, or North to invite auspicious forces.',
    },
    {
        "keywords": ['store', 'storage', 'depot', 'utility'],
        "primarySector": 'SW',
        "description": 'Heavy storage should be structured in the South-West to maintain balanced layout weight.',
    }
]

def get_vastu_rule_for_room(room_name: str) -> Optional[Dict[str, Any]]:
    name_lower = room_name.lower()
    for rule in VASTU_RULES:
        for kw in rule["keywords"]:
            if kw in name_lower:
                return rule
    return None

def get_sector_coordinates(sector: str, xlim: float, ylim: float) -> Dict[str, float]:
    cx = xlim / 2.0
    cy = ylim / 2.0
    rx = xlim * 0.28
    ry = ylim * 0.28

    if sector == 'NE':
        return {"x": cx + rx, "y": cy + ry}
    elif sector == 'NW':
        return {"x": cx - rx, "y": cy + ry}
    elif sector == 'SE':
        return {"x": cx + rx, "y": cy - ry}
    elif sector == 'SW':
        return {"x": cx - rx, "y": cy - ry}
    elif sector == 'N':
        return {"x": cx, "y": cy + ry}
    elif sector == 'S':
        return {"x": cx, "y": cy - ry}
    elif sector == 'E':
        return {"x": cx + rx, "y": cy}
    elif sector == 'W':
        return {"x": cx - rx, "y": cy}
    else:  # 'B' or default
        return {"x": cx, "y": cy}

def preadjust_rooms_for_vastu(rooms: List[Room], xlim: float, ylim: float) -> List[Room]:
    staggered_count: Dict[str, int] = {}
    adjusted = []

    for room in rooms:
        r = deepcopy(room)
        rule = get_vastu_rule_for_room(r.name)
        if rule:
            sector = rule["primarySector"]
            target = get_sector_coordinates(sector, xlim, ylim)

            if sector not in staggered_count:
                staggered_count[sector] = 0
            
            stagger_index = staggered_count[sector]
            staggered_count[sector] += 1
            
            stagger_x = ((stagger_index % 3) - 1) * 2.0
            stagger_y = (math.floor(stagger_index / 3) - 1) * 2.0

            r.x = target["x"] - (r.w or 0) / 2.0 + stagger_x
            r.y = target["y"] - (r.h or 0) / 2.0 + stagger_y
            
        adjusted.append(r)
        
    return adjusted

def evaluate_vastu_penalty(layout: List[Room], xlim: float, ylim: float) -> float:
    if not layout:
        return 0.0

    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    for r in layout:
        if r.x < min_x: min_x = r.x
        if r.x + (r.w or 0) > max_x: max_x = r.x + (r.w or 0)
        if r.y < min_y: min_y = r.y
        if r.y + (r.h or 0) > max_y: max_y = r.y + (r.h or 0)

    if min_x == float('inf'):
        return 0.0

    layout_center_x = (min_x + max_x) / 2.0
    layout_center_y = (min_y + max_y) / 2.0
    lw = max(1.0, max_x - min_x)
    lh = max(1.0, max_y - min_y)

    total_penalty = 0.0

    for r in layout:
        if getattr(r, 'isCorridor', False):
            continue

        rule = get_vastu_rule_for_room(r.name)
        if not rule:
            continue

        sector = rule["primarySector"]
        rx = (r.x + (r.w or 0) / 2.0) - layout_center_x
        ry = (r.y + (r.h or 0) / 2.0) - layout_center_y

        is_valid = False
        norm_x = rx / lw
        norm_y = ry / lh
        tolerance = 0.08

        if sector == 'NE':
            is_valid = (norm_x >= -tolerance and norm_y >= -tolerance)
        elif sector == 'NW':
            is_valid = (norm_x <= tolerance and norm_y >= -tolerance)
        elif sector == 'SE':
            is_valid = (norm_x >= -tolerance and norm_y <= tolerance)
        elif sector == 'SW':
            is_valid = (norm_x <= tolerance and norm_y <= tolerance)
        elif sector == 'N':
            is_valid = (norm_y >= -tolerance)
        elif sector == 'S':
            is_valid = (norm_y <= tolerance)
        elif sector == 'E':
            is_valid = (norm_x >= -tolerance)
        elif sector == 'W':
            is_valid = (norm_x <= tolerance)
        elif sector == 'B':
            is_valid = (abs(norm_x) < 0.2 and abs(norm_y) < 0.2)

        if not is_valid:
            target_x = 0.0
            target_y = 0.0
            rx_target = lw * 0.25
            ry_target = lh * 0.25

            if sector == 'NE': target_x = rx_target; target_y = ry_target
            elif sector == 'NW': target_x = -rx_target; target_y = ry_target
            elif sector == 'SE': target_x = rx_target; target_y = -ry_target
            elif sector == 'SW': target_x = -rx_target; target_y = -ry_target
            elif sector == 'N': target_x = 0.0; target_y = ry_target
            elif sector == 'S': target_x = 0.0; target_y = -ry_target
            elif sector == 'E': target_x = rx_target; target_y = 0.0
            elif sector == 'W': target_x = -rx_target; target_y = 0.0
            elif sector == 'B': target_x = 0.0; target_y = 0.0

            dist = math.hypot(rx - target_x, ry - target_y)
            total_penalty += dist * 150.0

    return total_penalty
