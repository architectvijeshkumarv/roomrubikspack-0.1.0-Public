import roomrubikspack as rr

def main():
    # 1. (Optional) Set the measurement unit to meters ('m') or feet ('f')
    rr.settings(unit="m")

    # 2. View or modify the construction grid (used by dimension generation)
    # The grid uses standard architectural modules. You can add or remove values.
    rr.constructiongrid(add=5.0)
    rr.constructiongrid(remove=9.0)
    rr.constructiongrid(reset=True) # Reset back to defaults
    rr.constructiongrid() # Show current grid

    # 4. Add Rooms
    rr.room("living",   "Living Room",  area=20.0, startSpace=True, color="#f2e6d9")
    rr.room("kitchen",  "Kitchen",      w=3.0, h=3.0, color="#d9f2d9")
    rr.room("bed1",     "Master Bed",   area=16.0, color="#d9d9f2")
    rr.room("bath1",    "Attached Bath", area=4.0, attachedSpace=True, color="#e6f2ff")

    # (Optional) Define a site boundary
    rr.site([{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}])

    # 5. Add Connectivity (Adjacency requirements)
    rr.connectivity(
        ("living", "kitchen"),
        ("living", "bed1"),
        ("bed1",   "bath1")
    )

    # 6. (Optional) Show the connectivity graph locally
    rr.connectivityshow()

    # 7. Add Soft Constraints for the Genetic Algorithm
    rr.constraint("position", "bed1", "N")
    rr.constraint("area", None, 120)
    rr.constraint("perimeter", None, "minimize")

    # 8. Request baseline dimensions from the server (optional, GA will dynamically explore dimensions within area bounds)
    rr.dimensiongen(avar=0.10, mar=1.5)

    # 9. Generate layout variations using the Genetic Algorithm (calls server)
    # The engine will dynamically explore different grid-snapped dimension permutations for rooms defined by area!
    rr.generatelayout(lvar=0.5, sgap=1.0, max_variations=5)

    # 10. (Optional) Show the layout visually (customizing labels: name, id, dim, area)
    rr.showlayout(n=1, label=["name", "id", "dim", "area"])

    # 11. (Optional) Export the layout
    rr.exportlayout(n=1, filepath="output_layout.json")
    rr.exportlayout(n=1, filepath="output_layout.dxf")

    # Wait for the user to close all plots before exiting the script
    # rr.wait_for_plots()

if __name__ == "__main__":
    main()
