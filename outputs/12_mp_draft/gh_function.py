""" Summary:
The script builds a vertical facade by creating two aligned Rhino cuboids (base and top) and a series of slender ‘window’ cuboids spaced across the width. Window boxes span the full depth and height (to top_height), computed with divisions and spacing so they tile evenly. All boxes are converted to Breps and the code iteratively subtracts each window Brep from the structural Breps using RhinoCommon’s CreateBooleanDifference with a 1e-6 tolerance. Failed operations are handled by skipping; successful results replace the working set, producing non‑intersecting, subtractively sculpted Breps. Finally three sample variants are generated and packed into a Grasshopper DataTree output."""

#! python 3
function_code = """def create_vertical_structure(base_width=20.0, base_height=60.0, top_height=90.0, depth=20.0, window_width=2.0, window_height=2.0, divisions=5):
    \"""
    Creates a vertical architectural structure with a variation of cuboids using boolean operations in RhinoCommon.
    The design incorporates vertical grooves resembling windows to resemble the reference images given.

    Parameters:
    - base_width: Width of the base cuboid.
    - base_height: Height of the base cuboid.
    - top_height: Height of the entire structure.
    - depth: Depth of the cuboids.
    - window_width: Width of the windows (grooves).
    - window_height: Height of the windows (grooves).
    - divisions: Number of vertical divisions for windows.

    Returns:
    - List of Breps representing the final architectural structure without intersecting geometries.
    \"""
    import Rhino.Geometry as rg

    # Create base and top cuboids
    base_cuboid = rg.Box(rg.Plane.WorldXY, rg.Interval(-base_width/2, base_width/2), rg.Interval(-depth/2, depth/2), rg.Interval(0, base_height))
    top_cuboid = rg.Box(rg.Plane.WorldXY, rg.Interval(-base_width/2, base_width/2), rg.Interval(-depth/2, depth/2), rg.Interval(base_height, top_height))
    
    # Create windows (grooves)
    window_cuboids = []
    total_groove_width = divisions * window_width
    spacing = (base_width - total_groove_width) / (divisions + 1)
    current_x = -base_width/2 + spacing
    
    for i in range(divisions):
        window_cuboid = rg.Box(rg.Plane.WorldXY, rg.Interval(current_x, current_x + window_width), rg.Interval(-depth/2, depth/2), rg.Interval(0, top_height))
        window_cuboids.append(window_cuboid.ToBrep())
        current_x += window_width + spacing
    
    # Subtract window cuboids from the structures
    base_brep = base_cuboid.ToBrep()
    top_brep = top_cuboid.ToBrep()
    
    # Perform Boolean Difference iteratively and handle potential failures
    all_breps = [base_brep, top_brep]
    for window_brep in window_cuboids:
        temp_breps = []
        for brep in all_breps:
            boolean_diff = rg.Brep.CreateBooleanDifference([brep], [window_brep], 1e-6)
            if boolean_diff:
                temp_breps.extend(boolean_diff)
        all_breps = temp_breps

    return all_breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = create_vertical_structure(base_width=30.0, base_height=50.0, top_height=120.0, depth=25.0, window_width=2.5, window_height=4.0, divisions=6)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = create_vertical_structure(base_width=40.0, base_height=80.0, top_height=160.0, depth=30.0, window_width=3.0, window_height=5.0, divisions=8)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = create_vertical_structure(base_width=25.0, base_height=45.0, top_height=110.0, depth=22.0, window_width=1.8, window_height=3.5, divisions=7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
