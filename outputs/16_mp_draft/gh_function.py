""" Summary:
The script builds a vertical facade by creating a main rectangular solid as the building mass, then carving repeated window voids and frames. Window counts derive from base dimensions, window size, and spacing to tile facades. In nested loops it places cuboid window volumes at computed positions and performs subtractive boolean differences to cut openings from the main Brep, updating the main geometry after each successful operation. Finally it appends a gutter box along the roof edge as a roof detail and returns the resulting Brep list. Multiple sample calls produce varied proportions while preserving consistent facade detailing and textures."""

#! python 3
function_code = """def generate_vertical_structure(base_width, base_depth, height, facade_window_width, facade_window_height, window_spacing):
    \"""
    Generate a vertical architectural structure using variations of cuboids and rectangular geometries
    with facades detailed to resemble reference images. The structure includes voids, windows, and
    additional facade details ensuring a non-flat appearance. The roof/ceiling also features detail elements.

    Parameters:
    - base_width: The width of the base of the structure (meters).
    - base_depth: The depth of the base of the structure (meters).
    - height: The total height of the structure (meters).
    - facade_window_width: The width of each window on the facade (meters).
    - facade_window_height: The height of each window on the facade (meters).
    - window_spacing: The horizontal spacing between adjacent windows on the facade (meters).

    Returns:
    - A list of Brep objects: A list containing the Brep geometries of the completed architectural structure.
    \"""
    import Rhino.Geometry as rg

    structures = []

    # Create the main body of the structure
    base = rg.Box(rg.Plane.WorldXY, rg.Interval(0, base_width), rg.Interval(0, base_depth), rg.Interval(0, height))
    main_brep = base.ToBrep()
    structures.append(main_brep)

    # Facade details using extrusions and windows
    count_x = int(base_width / (facade_window_width + window_spacing))
    count_y = int(base_depth / (facade_window_width + window_spacing))

    # Subtractive details for each facade
    for i in range(count_x):
        for j in range(count_y):
            x_pos = i * (facade_window_width + window_spacing) + window_spacing / 2
            y_pos = j * (facade_window_width + window_spacing) + window_spacing / 2
            if x_pos + facade_window_width < base_width and y_pos + facade_window_width < base_depth:
                window_frame = rg.Box(
                    rg.Plane(rg.Point3d(x_pos, 0, height - facade_window_height), rg.Vector3d.ZAxis),
                    rg.Interval(0, facade_window_width), rg.Interval(0, facade_window_width), rg.Interval(0, -facade_window_height)
                ).ToBrep()

                # Subtract windows from the main brep
                bool_result = rg.Brep.CreateBooleanDifference([main_brep], [window_frame], 0.01)
                if bool_result:
                    main_brep = bool_result[0]

    structures.append(main_brep)

    # Roof details: add a simple gutter along the edges
    gutter_width = 0.5
    gutter_height = 0.2
    gutter_depth = 0.2

    gutter_box = rg.Box(
        rg.Plane(rg.Point3d(0, 0, height), rg.Vector3d.ZAxis),
        rg.Interval(0, base_width), rg.Interval(0, gutter_depth), rg.Interval(0, gutter_height)
    ).ToBrep()

    structures.append(gutter_box)

    return [struc for struc in structures if struc is not None]"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_vertical_structure(10.0, 6.0, 30.0, 1.2, 2.0, 0.6)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_vertical_structure(20.0, 8.0, 45.0, 1.5, 2.5, 0.8)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_vertical_structure(15.0, 7.0, 50.0, 1.1, 2.2, 0.7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
