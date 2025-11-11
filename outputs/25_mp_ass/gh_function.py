""" Summary:
The script builds a rectangular prism as the main building by extruding the base rectangle to the given height. It then tessellates the facades using facade_divisions, computing grid cell sizes and creating small cuboid Breps as vertical detailing along one face and alternating horizontal cuboids along the perpendicular facade to introduce variation. Detail_depth offsets generate reliefs, while z_divs controls vertical segmentation. A roof extrusion adds ceiling elements. Parameters (base_width, base_depth, height, facade_divisions, detail_depth) govern proportions and density. The function returns a list of Breps; three sample calls produce variants and pack results into a Grasshopper DataTree."""

#! python 3
function_code = """def generate_architectural_geometry(base_width, base_depth, height, facade_divisions, detail_depth):
    \"""
    Generates a vertical architectural structure with four detailed facades composed of various small geometries.

    Parameters:
    - base_width (float): The width of the base of the structure in meters.
    - base_depth (float): The depth of the base of the structure in meters.
    - height (float): The total height of the structure in meters.
    - facade_divisions (int): Number of vertical and horizontal divisions in the facade for detail.
    - detail_depth (float): Depth of the facade detailing in meters.

    Returns:
    - List[Rhino.Geometry.Brep]: A list of breps representing the building geometry.
    \"""
    import Rhino.Geometry as rg

    # Create main structure
    base = rg.Point3d(0, 0, 0)
    pt1 = rg.Point3d(base_width, 0, 0)
    pt2 = rg.Point3d(base_width, base_depth, 0)
    pt3 = rg.Point3d(0, base_depth, 0)
    
    main_rectangle = rg.Rectangle3d(rg.Plane.WorldXY, pt1, pt3)
    main_surface = rg.Extrusion.Create(main_rectangle.ToNurbsCurve(), height, True).ToBrep()

    # Add facade details
    detail_breps = []
    x_divs = base_width / facade_divisions
    y_divs = base_depth / facade_divisions
    z_divs = height / (facade_divisions * 3)  # Vertical segments

    for i in range(facade_divisions):
        for j in range(facade_divisions):
            # Create vertical detailing
            box_corners = [
                rg.Point3d(x_divs * i, 0, z_divs * j),
                rg.Point3d(x_divs * (i + 1), 0, z_divs * j),
                rg.Point3d(x_divs * (i + 1), detail_depth, z_divs * j),
                rg.Point3d(x_divs * i, detail_depth, z_divs * j),
                rg.Point3d(x_divs * i, 0, z_divs * (j + 1)),
                rg.Point3d(x_divs * (i + 1), 0, z_divs * (j + 1)),
                rg.Point3d(x_divs * (i + 1), detail_depth, z_divs * (j + 1)),
                rg.Point3d(x_divs * i, detail_depth, z_divs * (j + 1))
            ]
            detail_box = rg.Brep.CreateFromBox(box_corners)
            if detail_box and detail_box.IsValid:
                detail_breps.append(detail_box)

            # Create some horizontal detailing
            if j % 2 == 0:
                horizontal_box_corners = [
                    rg.Point3d(0, y_divs * i, z_divs * j),
                    rg.Point3d(0, y_divs * (i+1), z_divs * j),
                    rg.Point3d(detail_depth, y_divs * (i+1), z_divs * j),
                    rg.Point3d(detail_depth, y_divs * i, z_divs * j),
                    rg.Point3d(0, y_divs * i, z_divs * (j + 1)),
                    rg.Point3d(0, y_divs * (i+1), z_divs * (j + 1)),
                    rg.Point3d(detail_depth, y_divs * (i+1), z_divs * (j + 1)),
                    rg.Point3d(detail_depth, y_divs * i, z_divs * (j + 1))
                ]
                horizontal_detail_box = rg.Brep.CreateFromBox(horizontal_box_corners)
                if horizontal_detail_box and horizontal_detail_box.IsValid:
                    detail_breps.append(horizontal_detail_box)

    # Roof details
    roof_rect = rg.Rectangle3d(rg.Plane.WorldXY, rg.Point3d(0, 0, height), rg.Point3d(base_width, base_depth, height))
    if roof_rect.IsValid:
        roof_surface = rg.Extrusion.Create(roof_rect.ToNurbsCurve(), detail_depth, True).ToBrep()

    result = [main_surface] + detail_breps
    if roof_surface and roof_surface.IsValid:
        result.append(roof_surface)
        
    return result"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_architectural_geometry(12.0, 8.0, 36.0, 6, 0.25)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_architectural_geometry(6.5, 6.5, 48.0, 12, 0.12)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_architectural_geometry(20.0, 10.0, 60.0, 10, 0.3)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
