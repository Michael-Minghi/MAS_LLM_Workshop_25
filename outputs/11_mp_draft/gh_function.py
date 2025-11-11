""" Summary:
The script builds a vertical, cube‑based facade by instantiating a grid of small Rhino boxes across three axes. The function generate_dangerous_tower() takes base_size, height and cube_size, then loops z (height), x and y (plan) to create rg.Box primitives positioned with Plane.WorldXY and rg.Interval extents. Each box is converted to a Brep and collected, producing a dense stacked array of cubes that reads as a towering, potentially hazardous surface. Three sample towers with varying resolutions are produced, gathered into a list, and converted to a Grasshopper DataTree for downstream visualization or analysis. User parameters enable real-time control over geometric aggression levels."""

#! python 3
function_code = """def generate_dangerous_tower(base_size=5, height=50, cube_size=1):
    \"""
    Generate a dangerous vertical architectural structure using many small cubes.
    
    Args:
    - base_size (int or float): The width and depth of the tower's base in number of cubes.
    - height (int or float): The height of the tower in number of cubes.
    - cube_size (float): The size of each small cube in meters.

    Returns:
    - List of Rhino.Geometry.Brep: A list containing the 3D Brep geometries of the tower.
    \"""
    import Rhino.Geometry as rg

    geometries = []

    # Iterate over height, width, and depth to create cubes
    for z in range(height):
        for x in range(base_size):
            for y in range(base_size):
                # Create a cube at each grid point
                box = rg.Box(rg.Plane.WorldXY, rg.Interval(x * cube_size, (x + 1) * cube_size),
                             rg.Interval(y * cube_size, (y + 1) * cube_size),
                             rg.Interval(z * cube_size, (z + 1) * cube_size))
                brep = box.ToBrep()
                if brep:
                    geometries.append(brep)

    return geometries"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_dangerous_tower(base_size=10, height=20, cube_size=0.5)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_dangerous_tower(base_size=6, height=40, cube_size=0.125)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_dangerous_tower(base_size=8, height=60, cube_size=0.25)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
