""" Summary:
The script builds a vertical architectural facade by stacking rectangular box segments to form a tall volume, then scatters many small cuboid details across its surfaces. Inputs (base_width, height, segment_count, detail_density) define overall size, vertical segmentation, and number of facade elements. segment_height divides the tower; each main segment is created as an rg.Box converted to a Brep. A seeded random generator places small detail boxes with sizes between detail_min_size and detail_max_size at random x,y,z positions, producing windows, voids, gutters and surface relief. Three sample structures are generated and packaged into a Grasshopper DataTree for modeling and visualization workflows."""

#! python 3
function_code = """def generate_vertical_structure(base_width, height, segment_count, detail_density):
    \"""
    Generate a vertical architectural structure with detailed facades using small cuboids and linear geometries.
    
    Parameters:
    - base_width: float, the width of the base of the structure in meters.
    - height: float, the total height of the structure in meters.
    - segment_count: int, the number of vertical segments in the structure.
    - detail_density: int, the number of small details to add to the facade for complexity.
    
    Returns:
    - List of Breps representing the 3D model of the structure with facade details.
    \"""
    import Rhino.Geometry as rg
    import random

    geometries = []
    random.seed(42)  # Ensures replicability

    segment_height = height / segment_count
    detail_min_size = base_width * 0.02
    detail_max_size = base_width * 0.1

    # Create main vertical segments
    for i in range(segment_count):
        pt_bottom = rg.Point3d(0, 0, i * segment_height)
        pt_top = rg.Point3d(0, 0, (i + 1) * segment_height)
        segment = rg.Box(rg.Plane.WorldXY, rg.Interval(-base_width / 2, base_width / 2), rg.Interval(-base_width / 2, base_width / 2), rg.Interval(pt_bottom.Z, pt_top.Z))
        geometries.append(segment.ToBrep())

    # Add detailed small cuboids and linear geometries as facade details
    for _ in range(detail_density):
        x_size = random.uniform(detail_min_size, detail_max_size)
        y_size = random.uniform(detail_min_size, detail_max_size)
        z_size = random.uniform(detail_min_size, detail_max_size)
        x_pos = random.uniform(-base_width / 2, base_width / 2)
        y_pos = random.uniform(-base_width / 2, base_width / 2)
        z_pos = random.uniform(0, height)

        detail_box = rg.Box(rg.Plane.WorldXY, rg.Interval(x_pos, x_pos + x_size), rg.Interval(y_pos, y_pos + y_size), rg.Interval(z_pos, z_pos + z_size))
        geometries.append(detail_box.ToBrep())

    return geometries"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_vertical_structure(6.0, 30.0, 12, 150)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_vertical_structure(8.5, 40.0, 16, 200)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_vertical_structure(5.0, 20.0, 10, 100)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
