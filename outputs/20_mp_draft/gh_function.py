""" Summary:
This script divides a vertical volume into stacked segments, creating a main Box Brep per segment. For each segment it subtracts numerous small cuboidal facade elements—random-width/depth/height boxes—using boolean difference to carve recesses and voids. It then subtracts window boxes along edges to form openings. Random.seed(0) ensures reproducible variation in counts and offsets. Segments accumulate as independent Breps with non‑intersecting geometry because details are subtracted from the parent box. Finally a shallow roof box with surface detail is appended. Multiple calls produce varied sizes and segment counts to generate facade systems resembling the reference composition, and add gutter-like linear trim elements."""

#! python 3
function_code = """def generate_vertical_structure(base_width, base_depth, total_height, segment_count):
    \"""
    Generates a vertical architectural structure using variations of cuboids
    and other linear rectangular geometries with detailed facades.

    Parameters:
    - base_width: Width of the base of the building in meters.
    - base_depth: Depth of the base of the building in meters.
    - total_height: Total height of the building in meters.
    - segment_count: Number of segments to divide the structure into along its height.

    Returns:
    - List of RhinoCommon Breps representing the 3D geometries of the building.
    \"""
    import Rhino.Geometry as rg
    import random

    random.seed(0)  # Ensure replicability

    geometries = []
    segment_height = total_height / segment_count

    # Create vertical segments
    for i in range(segment_count):
        segment_base = rg.Point3d(0, 0, i * segment_height)
        main_geom = rg.Box(
            rg.Plane(segment_base, rg.Vector3d.ZAxis),
            rg.Interval(-base_width / 2, base_width / 2),
            rg.Interval(-base_depth / 2, base_depth / 2),
            rg.Interval(0, segment_height),
        ).ToBrep()

        # Create subtractive facade detail
        num_facade_elements = random.randint(8, 12)
        for _ in range(num_facade_elements):
            facade_width = base_width * 0.1
            facade_depth = base_depth * 0.1
            facade_height = random.uniform(segment_height * 0.5, segment_height * 0.9)
            offset_x = random.uniform(-base_width / 2 + facade_width, base_width / 2 - facade_width)
            offset_y = random.uniform(-base_depth / 2 + facade_depth, base_depth / 2 - facade_depth)

            detail_geom = rg.Box(
                rg.Plane(
                    rg.Point3d(offset_x, offset_y, i * segment_height),
                    rg.Vector3d.ZAxis
                ),
                rg.Interval(-facade_width / 2, facade_width / 2),
                rg.Interval(-facade_depth / 2, facade_depth / 2),
                rg.Interval(0, facade_height)
            ).ToBrep()

            boolean_result = rg.Brep.CreateBooleanDifference([main_geom], [detail_geom], 0.001)
            if boolean_result and len(boolean_result) > 0:
                main_geom = boolean_result[0]

        # Add windows
        num_windows = random.randint(4, 6)
        for _ in range(num_windows):
            window_width = base_width * 0.05
            window_depth = base_depth * 0.02
            window_height = random.uniform(1, 2)
            window_x = random.uniform(-base_width / 2 + window_width, base_width / 2 - window_width)
            window_y = random.choice([(base_depth / 2 - window_depth), (-base_depth / 2 + window_depth)])

            window_geom = rg.Box(
                rg.Plane(
                    rg.Point3d(window_x, window_y, i * segment_height + facade_height),
                    rg.Vector3d.ZAxis
                ),
                rg.Interval(-window_width / 2, window_width / 2),
                rg.Interval(-window_depth / 2, window_depth / 2),
                rg.Interval(0, window_height)
            ).ToBrep()

            boolean_result = rg.Brep.CreateBooleanDifference([main_geom], [window_geom], 0.001)
            if boolean_result and len(boolean_result) > 0:
                main_geom = boolean_result[0]

        geometries.append(main_geom)

    # Roof details
    roof_height = 0.5
    roof_geom = rg.Box(
        rg.Plane(rg.Point3d(0, 0, total_height), rg.Vector3d.ZAxis),
        rg.Interval(-base_width / 2, base_width / 2),
        rg.Interval(-base_depth / 2, base_depth / 2),
        rg.Interval(0, roof_height)
    ).ToBrep()

    geometries.append(roof_geom)

    return geometries"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_vertical_structure(20, 12, 80, 8)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_vertical_structure(18, 14, 72, 9)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_vertical_structure(14, 10, 70, 7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
