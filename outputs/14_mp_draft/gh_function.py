""" Summary:
The script builds a tall base box, then subdivides its width into vertical panel boxes that extrude outward slightly. It also creates small window boxes near the top. Using Rhino.Geometry, all geometry is converted to Breps. For each panel the script performs subtractive Boolean differences with the window boxes so openings are cut out without intersecting geometry. Valid resulting Breps are collected alongside the base volume to form the facade assembly. Multiple parameter sets generate three sample façades with different dimensions. Finally the lists of Breps are converted into a Grasshopper DataTree for downstream use in Grasshopper workflows and rendering."""

#! python 3
function_code = """def generate_vertical_structure(base_width=10, base_depth=10, height=60, detail_depth=0.5):
    \"""
    Generates a vertical architectural structure resembling a series of cuboids and linear elements 
    creating a detailed façade. The design draws inspiration from modernist geometric towers with 
    vertical articulations and repetitive patterns. 

    Parameters:
    base_width (float): The width of the base of the structure (meters).
    base_depth (float): The depth of the base of the structure (meters).
    height (float): The total height of the structure (meters).
    detail_depth (float): The depth of the façade's detail elements (meters).

    Returns:
    List[Brep]: A list of Brep objects representing the 3D geometry of the structure.
    \"""
    import Rhino.Geometry as rg

    # Base structure
    base_box = rg.Box(rg.Plane.WorldXY, rg.Interval(0, base_width), rg.Interval(0, base_depth), rg.Interval(0, height))
    base_brep = base_box.ToBrep()

    # Vertical detail panelization
    panel_count = 10
    panel_width = base_width / panel_count
    panels = []

    for i in range(panel_count):
        panel_origin_x = i * panel_width
        panel_box = rg.Box(
            rg.Plane.WorldXY,
            rg.Interval(panel_origin_x, panel_origin_x + panel_width),
            rg.Interval(0, detail_depth),
            rg.Interval(0, height)
        )
        panels.append(panel_box.ToBrep())

    # Windows near the top
    window_count = 5
    window_width = base_width / window_count
    windows = []

    for i in range(window_count):
        window_origin_x = i * window_width + (window_width - detail_depth) / 2
        window_box = rg.Box(
            rg.Plane.WorldXY,
            rg.Interval(window_origin_x, window_origin_x + detail_depth),
            rg.Interval(detail_depth, base_depth),
            rg.Interval(height - detail_depth * 2, height)
        )
        windows.append(window_box.ToBrep())

    # Subtract windows from the panels
    structure = [base_brep]
    for panel in panels:
        results = rg.Brep.CreateBooleanDifference([panel], windows, 0.01)
        if results:
            valid_panels = [result for result in results if result.IsValid]
            structure.extend(valid_panels)

    return structure"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_vertical_structure(base_width=20, base_depth=12, height=80, detail_depth=0.6)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_vertical_structure(base_width=25.0, base_depth=15.0, height=120.0, detail_depth=0.8)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_vertical_structure(base_width=12, base_depth=6, height=50, detail_depth=0.3)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
