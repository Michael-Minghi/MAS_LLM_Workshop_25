""" Summary:
The script defines a parametric function create_chicken_garage(length, width, height, window_count) that builds a simplified 'chicken garage' as a tall rectangular volume (main_box) and adds repeated vertical facade elements and small windows. It creates a base Brep box for the building, computes evenly spaced vertical fins along the length, and extrudes narrow boxes as facade elements. Windows are placed near the top, sized relative to overall dimensions and extruded inward. The function returns a list of Brep/surface geometries. The script then generates three sample instances with different parameters and converts them into a Grasshopper DataTree for downstream use and simple visualization."""

#! python 3
function_code = """def create_chicken_garage(length, width, height, window_count):
    \"""
    This function generates a parametric 3D model of a chicken garage, resembling a
    tall, rectangular building with vertical elements and windows.

    Parameters:
    - length: The length of the garage along the X-axis (in meters).
    - width: The width of the garage along the Y-axis (in meters).
    - height: The height of the garage along the Z-axis (in meters).
    - window_count: The number of windows on the top facade.

    Returns:
    - A list of Brep geometries representing the 3D model of the chicken garage.
    \"""

    import Rhino.Geometry as rg

    # Main block
    base_point = rg.Point3d(0, 0, 0)
    main_box = rg.Box(rg.Plane.WorldXY, rg.Interval(0, length), rg.Interval(0, width), rg.Interval(0, height))
    brep_main = main_box.ToBrep()

    # Vertical facade elements
    num_facade_elements = 10
    vertical_elements = []
    element_width = length / (num_facade_elements + 1)
    element_height = height * 0.8
    element_dist = length / (num_facade_elements + 1)

    for i in range(1, num_facade_elements + 1):
        x_offset = element_dist * i
        element_box = rg.Box(rg.Plane.WorldXY, 
                             rg.Interval(x_offset - element_width / 2, x_offset + element_width / 2), 
                             rg.Interval(0, width * 0.1), 
                             rg.Interval(0, element_height))
        vertical_elements.append(element_box.ToBrep())

    # Windows
    window_height = height * 0.05
    window_width = length * 0.05
    windows = []

    for i in range(window_count):
        x_offset = (length / (window_count + 1)) * (i + 1)
        window_base_center = rg.Point3d(x_offset, width, height - window_height / 2)
        window_rect = rg.Rectangle3d(rg.Plane(window_base_center, rg.Vector3d.ZAxis), window_width, window_height)
        window_surface = rg.Surface.CreateExtrusion(window_rect.ToNurbsCurve(), rg.Vector3d(-0.1, 0, 0))
        windows.append(window_surface)

    # Return all elements
    return [brep_main] + vertical_elements + windows"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = create_chicken_garage(12.0, 6.0, 4.5, 6)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = create_chicken_garage(15.0, 7.5, 5.0, 8)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = create_chicken_garage(10.0, 4.5, 3.2, 5)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
