""" Summary:
The script defines a function that builds a vertically stacked facade composed of cubic sections and corner spheres. It divides the requested total height into num_sections, creates a box for each section centered vertically at incremental heights, and converts boxes to Breps. After stacking, it computes a sphere radius as 10% of the smaller base dimension and places four spheres at the top-corner coordinates. The function returns all Breps. The script then calls the function with three parameter sets, collects the resulting geometry lists, converts them into a Grasshopper DataTree, and prints success for downstream Grasshopper usage and visualization steps."""

#! python 3
function_code = """def create_dangerous_vertical_structure(base_width, base_depth, height, num_sections):
    \"""
    Generates a dangerous vertical architectural structure using cubes and spheres.
    
    Parameters:
    - base_width (float): The width of the base of the structure in meters.
    - base_depth (float): The depth of the base of the structure in meters.
    - height (float): The total height of the structure in meters.
    - num_sections (int): The number of sections the structure is divided into.
    
    Returns:
    - List[gh.Brep]: A list of Breps representing the structure.
    \"""
    import Rhino.Geometry as rg

    breps = []
    section_height = height / num_sections
    
    # Create base cube shapes, stacked vertically
    for i in range(num_sections):
        center_point = rg.Point3d(0, 0, i * section_height)
        cube = rg.Box(rg.Plane(center_point, rg.Vector3d.ZAxis), rg.Interval(-base_width/2, base_width/2), rg.Interval(-base_depth/2, base_depth/2), rg.Interval(0, section_height))
        breps.append(cube.ToBrep())
    
    # Adding spheres to the top corners of the cube structure
    top_center = rg.Point3d(0, 0, height)
    sphere_radius = min(base_width, base_depth) * 0.1
    sphere_positions = [
        rg.Point3d(base_width / 2, base_depth / 2, height),
        rg.Point3d(-base_width / 2, base_depth / 2, height),
        rg.Point3d(base_width / 2, -base_depth / 2, height),
        rg.Point3d(-base_width / 2, -base_depth / 2, height)
    ]
    
    for pos in sphere_positions:
        sphere = rg.Sphere(pos, sphere_radius)
        breps.append(sphere.ToBrep())
    
    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = create_dangerous_vertical_structure(2.5, 1.5, 12.0, 6)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = create_dangerous_vertical_structure(3.0, 0.6, 18.0, 9)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = create_dangerous_vertical_structure(4.0, 2.0, 20.0, 10)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
