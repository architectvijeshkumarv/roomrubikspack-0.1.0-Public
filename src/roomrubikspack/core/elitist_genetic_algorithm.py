"""
roomrubikspack/core/elitist_genetic_algorithm.py

Implements a constrained Elitist Genetic Algorithm (GA) specifically designed
to optimize 2D rectangular floorplan layouts.

This GA maintains a population of "Chromosomes", where each chromosome is a complete
valid floorplan layout (a list of Room objects with assigned x, y, width, height).
It evaluates the "fitness" of each layout using a custom cost-function that heavily
penalizes overlaps, boundary violations (site constraints), un-met adjacencies,
and Vastu non-compliance.
"""
import math
import random
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from .generator import generate_layout, count_corners, calculate_perimeter
from ..utils.constraints import evaluate_constraints_penalty, preadjust_rooms_for_constraints
from ..utils.vastu import evaluate_vastu_penalty, preadjust_rooms_for_vastu

def is_point_in_polygon(x: float, y: float, polygon: List[Dict[str, float]]) -> bool:
    """
    Ray-casting algorithm to check point containment in a site polygon.
    It works by casting an imaginary ray from the point (x, y) horizontally to the right.
    If the ray crosses the polygon boundary an odd number of times, the point is inside.
    If it crosses an even number of times, the point is outside.
    """
    n = len(polygon)
    inside = False
    p1x = polygon[0]['x']
    p1y = polygon[0]['y']
    for i in range(n + 1):
        p2x = polygon[i % n]['x']
        p2y = polygon[i % n]['y']
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if p1x == p2x or x <= xinters:
                    inside = not inside
        p1x, p1y = p2x, p2y
    return inside

class Chromosome:
    def __init__(self, layout: List[Any], score: float):
        self.layout = layout
        self.score = score

class ElitistGeneticAlgorithm:
    def __init__(self, rooms: List[Any], connections: List[Any], settings: Dict[str, Any], start_room_id: str, pop_size: int = 20, max_generations: int = 10, mutation_rate: float = 0.2, constraints: Optional[List[Dict[str, Any]]] = None, site_points: Optional[List[Dict[str, float]]] = None):
        self.connections = connections
        self.settings = settings.copy() if settings else {}
        if self.settings.get("locationVariation", 0) > 0:
            self.settings["randomizeParents"] = True
        self.start_room_id = start_room_id
        self.pop_size = pop_size
        self.max_generations = max_generations
        self.mutation_rate = mutation_rate
        self.constraints = constraints or []
        self.site_points = site_points

        xl = settings.get("xlim", 30)
        yl = settings.get("ylim", 30)
        
        # Apply Vastu preadjustments first if enabled, then override with custom constraints
        current_rooms = rooms
        if self.settings.get("vastu", False):
            current_rooms = preadjust_rooms_for_vastu(current_rooms, xl, yl)
            
        self.rooms = preadjust_rooms_for_constraints(current_rooms, xl, yl, self.constraints)

    def _has_valid_aspect_ratio(self, layout: List[Any], max_ratio: float = 2.5) -> bool:
        # Check if the room aspect ratio is within the max_ratio (to avoid excessively thin rooms)
        for r in layout:
            ratio = max(r.w / r.h, r.h / r.w) if r.h > 0 and r.w > 0 else 1.0
            if ratio > max_ratio:
                return False
        return True

    def _has_valid_overlaps(self, layout: List[Any], min_overlap: float = 1.1) -> bool:
        """
        Validates that all topologically connected rooms in the layout physically overlap
        each other by at least `min_overlap` (usually > 1.0m to account for a doorway).
        
        This prevents situations where two connected rooms are physically disjointed
        (gaps) or only touching at a single infinitesimally small corner point.
        """
        for conn in self.connections:
            rA = next((r for r in layout if r.id == conn.roomA), None)
            rB = next((r for r in layout if r.id == conn.roomB), None)
            if not rA or not rB:
                continue

            # Calculate how much the two rectangles overlap on the X and Y axes
            overlap_x = max(0.0, min(rA.x + rA.w, rB.x + rB.w) - max(rA.x, rB.x))
            overlap_y = max(0.0, min(rA.y + rA.h, rB.y + rB.h) - max(rA.y, rB.y))

            # Calculate the literal gap distance between them if they don't overlap
            gap_x = max(0.0, max(rA.x, rB.x) - min(rA.x + rA.w, rB.x + rB.w))
            gap_y = max(0.0, max(rA.y, rB.y) - min(rA.y + rA.h, rB.y + rB.h))

            if gap_x <= 0.1 and overlap_y >= min_overlap - 0.1: continue
            if gap_y <= 0.1 and overlap_x >= min_overlap - 0.1: continue

            return False
        return True

    def _calculate_score(self, layout: List[Any]) -> float:
        """
        The core fitness function for the GA. Evaluates a given layout variation
        and assigns it a mathematical "cost" (score). A lower score is better.
        The algorithm tries to minimize this score.
        """
        # Calculate base geometric metrics (corners and perimeter)
        # We penalize high corner counts to encourage clean, boxy, unified floorplans.
        corners = count_corners(layout)
        
        # Calculate intersections (vertices where walls meet). 
        # Fewer intersections imply a cleaner layout with fewer weird juts.
        unique_points = set()
        for r in layout:
            unique_points.add(f"{r.x},{r.y}")
            unique_points.add(f"{r.x + r.w},{r.y}")
            unique_points.add(f"{r.x},{r.y + r.h}")
            unique_points.add(f"{r.x + r.w},{r.y + r.h}")
        intersections = len(unique_points)

        perimeter = calculate_perimeter(layout)

        # Penalize bad aspect ratios (squarish rooms are preferred)
        aspect_penalty = 0.0
        for r in layout:
            ratio = max(r.w / r.h, r.h / r.w) if r.h > 0 and r.w > 0 else 1.0
            aspect_penalty += (math.pow(ratio, 2) * 5) if ratio > 1.5 else ratio

        # Penalize if generated area significantly deviates from target area
        area_penalty = 0.0
        for r in layout:
            orig_room = next((orig for orig in self.rooms if orig.id == r.id), None)
            
            target_area = None
            if orig_room:
                if getattr(orig_room, 'area', None) is not None:
                    target_area = orig_room.area
                elif getattr(orig_room, 'w', None) is not None and getattr(orig_room, 'h', None) is not None:
                    target_area = orig_room.w * orig_room.h
            
            if target_area is None:
                target_area = r.w * r.h

            actual_area = r.w * r.h
            diff = (actual_area - target_area) / target_area if target_area > 0 else 0
            if diff < 0:
                area_penalty += math.pow(abs(diff), 2) * 20
            else:
                area_penalty += abs(diff)

        # Custom Constraint penalty
        xl = self.settings.get("xlim", 30)
        yl = self.settings.get("ylim", 30)
        constraint_penalty = evaluate_constraints_penalty(layout, xl, yl, self.constraints)
        
        # Vastu penalty (if enabled)
        vastu_penalty = 0.0
        if self.settings.get("vastu", False):
            vastu_penalty = evaluate_vastu_penalty(layout, xl, yl)

        # Site boundary penalty
        site_penalty = 0.0
        if self.site_points:
            for r in layout:
                room_corners = [
                    (r.x, r.y),
                    (r.x + r.w, r.y),
                    (r.x, r.y + r.h),
                    (r.x + r.w, r.y + r.h)
                ]
                for cx, cy in room_corners:
                    if not is_point_in_polygon(cx, cy, self.site_points):
                        site_penalty += 10000.0  # Massive flat penalty for stepping out of bounds
                        # Additionally, apply a gradient penalty pulling the room towards the center of the site.
                        # This gradient helps the GA "learn" which direction it needs to move to get back inside.
                        scx = sum(p['x'] for p in self.site_points) / len(self.site_points)
                        scy = sum(p['y'] for p in self.site_points) / len(self.site_points)
                        dist = math.hypot(cx - scx, cy - scy)
                        site_penalty += dist * 100.0

        # Penalize missing rooms heavily
        missing_penalty = 0.0
        placed_ids = {r.id for r in layout}
        for orig in self.rooms:
            if orig.id not in placed_ids:
                missing_penalty += 50000.0

        # Combine all penalties into a final fitness score (lower is better)
        return (corners * 150) + (intersections * 80) + (perimeter * 2) + (aspect_penalty * 100) + (area_penalty * 500) + constraint_penalty + vastu_penalty + site_penalty + missing_penalty

    def _get_start_id(self) -> str:
        if self.settings.get("randomizeParents", False) and self.rooms:
            import random
            return random.choice(self.rooms).id
        return self.start_room_id

    def _generate_individual(self) -> Chromosome:
        layout = generate_layout(self.rooms, self.connections, self.settings, self._get_start_id(), self.site_points)
        if not layout:
            return Chromosome([], float('inf'))
        return Chromosome(layout, self._calculate_score(layout))

    def _initialize_population(self, target_topo_sig: Optional[str] = None) -> List[Chromosome]:
        population = []
        
        # If target_layout is provided, ensure the first individual exactly matches the target geometry
        target_layout = self.settings.get("target_topology_layout")
        if target_layout:
            population.append(Chromosome(target_layout, self._calculate_score(target_layout)))
            
        attempts = 0
        while len(population) < self.pop_size and attempts < self.pop_size * 50:
            attempts += 1
            ind = self._generate_individual()
            
            if not ind.layout or not self._has_valid_overlaps(ind.layout):
                continue
                
            if target_topo_sig:
                if self._compute_topo_sig(ind.layout) != target_topo_sig:
                    continue
            population.append(ind)
            
        # Fallback if we couldn't find enough matches
        while len(population) < self.pop_size:
            population.append(Chromosome([], float('inf')))
            
        population.sort(key=lambda x: x.score)
        return population

    def _compute_topo_sig(self, layout: List[Any]) -> str:
        if not layout: return ""
        sig_parts = []
        for c in self.connections:
            rA = next((r for r in layout if r.id == c.roomA), None)
            rB = next((r for r in layout if r.id == c.roomB), None)
            if rA and rB:
                # Support both object and dict access for target_topology_layout
                x_A = getattr(rA, 'x', rA.get('x', 0) if isinstance(rA, dict) else 0)
                y_A = getattr(rA, 'y', rA.get('y', 0) if isinstance(rA, dict) else 0)
                w_A = getattr(rA, 'w', rA.get('w', 0) if isinstance(rA, dict) else 0)
                h_A = getattr(rA, 'h', rA.get('h', 0) if isinstance(rA, dict) else 0)
                
                x_B = getattr(rB, 'x', rB.get('x', 0) if isinstance(rB, dict) else 0)
                y_B = getattr(rB, 'y', rB.get('y', 0) if isinstance(rB, dict) else 0)
                w_B = getattr(rB, 'w', rB.get('w', 0) if isinstance(rB, dict) else 0)
                h_B = getattr(rB, 'h', rB.get('h', 0) if isinstance(rB, dict) else 0)
                
                cxA, cyA = x_A + w_A/2, y_A + h_A/2
                cxB, cyB = x_B + w_B/2, y_B + h_B/2
                dx, dy = cxB - cxA, cyB - cyA
                rel = "R" if dx > 0 else "L"
                if abs(dy) > abs(dx):
                    rel = "T" if dy > 0 else "B"
                sig_parts.append(f"{c.roomA}-{rel}-{c.roomB}")
        return "|".join(sorted(sig_parts))

    def run_multiple(self, count: int) -> List[List[Any]]:
        import time
        start_time = time.time()
        
        target_layout = self.settings.get("target_topology_layout")
        target_topo_sig = self._compute_topo_sig(target_layout) if target_layout else None
        
        if target_topo_sig:
            self.max_generations *= 5  # Deep search for strict topological match
            
        population = self._initialize_population(target_topo_sig)

        for gen in range(self.max_generations):
            if time.time() - start_time > 45.0:
                print(f"Time limit reached at generation {gen}. Stopping early.")
                break
                
            new_population = []
            
            elite_count = max(1, int(self.pop_size * 0.2))
            for i in range(elite_count):
                new_population.append(population[i])

            attempts = 0
            while len(new_population) < self.pop_size and attempts < self.pop_size * 5:
                attempts += 1
                mutated_settings = self.settings.copy()
                base_var = mutated_settings.get("locationVariation", 0)
                mutated_settings["locationVariation"] = base_var * (1.0 + (random.random() * self.mutation_rate * 2 - self.mutation_rate))
                
                layout = generate_layout(self.rooms, self.connections, mutated_settings, self._get_start_id(), self.site_points)
                if not layout: continue
                
                if not self._has_valid_aspect_ratio(layout, 2.5): continue
                if not self._has_valid_overlaps(layout): continue
                
                if target_topo_sig:
                    if self._compute_topo_sig(layout) != target_topo_sig:
                        continue

                new_population.append(Chromosome(layout, self._calculate_score(layout)))
                
            while len(new_population) < self.pop_size:
                layout = generate_layout(self.rooms, self.connections, self.settings, self._get_start_id(), self.site_points)
                if layout:
                    new_population.append(Chromosome(layout, self._calculate_score(layout) + 10000))
                else:
                    new_population.append(Chromosome([], float('inf')))

            population = sorted(new_population, key=lambda x: x.score)

        unique_layouts = []
        seen_topo = set()
        
        # Pass 1: Strict topological uniqueness
        for ind in population:
            if not ind.layout: continue
            
            topo_sig = self._compute_topo_sig(ind.layout)
            if target_topo_sig and topo_sig != target_topo_sig:
                continue # Strictly enforce target topology if set
                
            if topo_sig not in seen_topo:
                seen_topo.add(topo_sig)
                unique_layouts.append({"layout": ind.layout, "score": ind.score, "topo_sig": topo_sig})
                if len(unique_layouts) >= count:
                    break

        # Pass 2: If we don't have enough topologically unique layouts, fall back to best geometric ones
        if len(unique_layouts) < count:
            seen_geom = set()
            for ind in population:
                if not ind.layout: continue
                
                if target_topo_sig and self._compute_topo_sig(ind.layout) != target_topo_sig:
                    continue
                    
                geom_sig = "|".join(sorted([f"{r.id}:{round(r.x/2)*2},{round(r.y/2)*2}" for r in ind.layout]))
                is_already_included = any(u["layout"] == ind.layout for u in unique_layouts)
                
                if geom_sig not in seen_geom and not is_already_included:
                    seen_geom.add(geom_sig)
                    unique_layouts.append({"layout": ind.layout, "score": ind.score})
                    if len(unique_layouts) >= count:
                        break

        # Strip internal signature field before returning
        return [{"layout": u["layout"], "score": u["score"]} for u in unique_layouts]
