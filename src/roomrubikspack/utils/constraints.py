from typing import List, Dict, Any, Optional

_global_constraints: List[Dict[str, Any]] = []

def add_constraint(constraint_type: str, room_id: Optional[str] = None, value: Any = None):
    """
    Appends a new constraint to the global constraint list.
    Called internally by rr.constraint().
    """
    _global_constraints.append({
        "type": constraint_type,   # One of: "position", "area", "perimeter"
        "room_id": room_id,        # Target room for positional constraints; None for global ones
        "value": value             # Meaning depends on type
    })

def clear_constraints():
    """Resets the global constraint list. Called by rr.init() at session start."""
    global _global_constraints
    _global_constraints = []
