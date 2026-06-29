"""
generators/dimension_generator.py

Generates valid width (w) and height (h) for a room given only its target area.

The generator uses a pre-expanded grid of architectural module sizes
(multiples of common modular increments like 1.2m, 1.5m, 1.8m, etc.)
roomrubikspack/generators/dimension_generator.py

This module contains the `DimensionGenerator` which maps target room areas (m²) 
to exact (width, height) combinations that align with standard architectural construction grids.

It precomputes a large set of possible combinations of (width * height = area)
from the base construction grids (e.g. 1.2, 1.5, ..., 9.0) and uses a custom internal
genetic algorithm (or greedy search) to select the optimal dimensions that minimize
excess area while preserving required aspect ratios.
"""

from typing import List, Dict, Any, Optional
import math


class DimensionGenerator:
    """
    Generates architecturally sensible room dimensions from a target area.

    The internal grid is built by expanding a set of base modular sizes
    (e.g. 1.2m, 1.5m, 1.8m, ...) into all their integer multiples up to
    `max_dimension`. This ensures generated dimensions align to standard
    construction module grids.
    """

    def __init__(
        self,
        base_grid_sizes: Optional[List[float]] = None,
        area_variation: float = 0.2,
        max_aspect_ratio: float = 1.5,
        max_dimension: float = 50.0
    ):
        """
        Args:
            base_grid_sizes  : seed modular increments in metres
                               (default: [1.2, 1.5, 1.8, 2.1, 2.4, 3.0, 4.5, 6.0, 7.5, 9.0])
            area_variation   : fraction by which the generated area may differ
                               from the target (default ±20%)
            max_aspect_ratio : maximum allowed long-side to short-side ratio
                               (default 1.5 → rooms cannot be more than 1:1.5)
            max_dimension    : maximum single dimension in metres (default 50m)
        """
        if base_grid_sizes is None:
            # Standard architectural module sizes (metres)
            base_grid_sizes = [1.2, 1.5, 1.8, 2.1, 2.4, 3.0, 4.5, 6.0, 7.5, 9.0]

        self.area_variation = area_variation
        self.max_aspect_ratio = max_aspect_ratio

        # Expand each base size into all integer multiples up to max_dimension
        expanded = set()
        for size in base_grid_sizes:
            if size <= 0:
                continue
            i = 1
            while i * size <= max_dimension:
                expanded.add(round(i * size, 2))
                i += 1

        # Sort the full grid for deterministic iteration
        self.grid_sizes = sorted(list(expanded))

    def get_possible_dimensions(self, area: float) -> List[Dict[str, float]]:
        """
        Returns all (w, h) pairs from the grid that:
          - have a combined area within `area_variation` of the target
          - do not exceed `max_aspect_ratio`

        Returns a list of dicts: [{"w": float, "h": float}, ...]
        sorted by (w, h) for determinism.
        """
        area_min = area * (1 - self.area_variation)   # Lower acceptable area bound
        area_max = area * (1 + self.area_variation)   # Upper acceptable area bound

        valid_dimensions = []
        for length in self.grid_sizes:
            for width in self.grid_sizes:
                current_area = length * width
                if area_min <= current_area <= area_max:
                    # Reject dimensions with too extreme an aspect ratio
                    aspect_ratio = max(length, width) / min(length, width)
                    if aspect_ratio <= self.max_aspect_ratio:
                        valid_dimensions.append({"w": length, "h": width})

        valid_dimensions.sort(key=lambda d: (d["w"], d["h"]))
        return valid_dimensions

    def get_best_dimension(self, area: float) -> Optional[Dict[str, float]]:
        """
        Returns the single best (w, h) pair for a target area.
        Scoring: minimise area deviation first, then prefer aspect ratios closer to 1:1.5.

        Returns None if no valid combination exists in the grid.
        """
        possibilities = self.get_possible_dimensions(area)
        if not possibilities:
            return None

        def evaluate(dim):
            area_diff = abs(dim["w"] * dim["h"] - area)   # Primary: area accuracy
            aspect_ratio = max(dim["w"], dim["h"]) / min(dim["w"], dim["h"])
            ratio_diff = abs(aspect_ratio - 1.5)           # Secondary: prefer ~1:1.5
            return (area_diff, ratio_diff)

        return min(possibilities, key=evaluate)

    def is_valid_dimension(self, w: float, h: float, target_area: float) -> bool:
        """
        Validates whether a given (w, h) pair satisfies all generator constraints.
        Useful for checking user-supplied dimensions before using them.

        Returns True if:
          - both w and h appear in the grid
          - the combined area is within the allowed variation
          - the aspect ratio does not exceed the maximum
        """
        area_min = target_area * (1 - self.area_variation)
        area_max = target_area * (1 + self.area_variation)
        current_area = w * h

        is_w_in_grid = any(abs(s - w) < 0.01 for s in self.grid_sizes)
        is_h_in_grid = any(abs(s - h) < 0.01 for s in self.grid_sizes)
        is_area_valid = area_min <= current_area <= area_max
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float('inf')
        is_aspect_ratio_valid = aspect_ratio <= self.max_aspect_ratio

        return is_w_in_grid and is_h_in_grid and is_area_valid and is_aspect_ratio_valid
