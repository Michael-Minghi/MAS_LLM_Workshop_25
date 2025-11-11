""" Summary:
The script builds a vertical tower as a Rhino Box then converts it to a Brep. It seeds randomness and generates numerous small cuboid/cube detail boxes placed across the faces according to detail_level, then subtracts them from the main tower via BooleanDifference to create non-intersecting voids and reliefs. It carves repetitive window voids near the top, and models shallow gutter cuboids on the roof, using Boolean operations (difference and union) with a small tolerance. Parameters control base width, depth, height and complexity. Outputs are validated Breps returned as the final facade assemblies ready for use in Grasshopper and exportable geometry."""

#! python 3
function_code = """def generate_vertical_structure(base_width=10, base_depth=10, height=50, detail_level=5):
    \"""
    Generates a vertical architectural structure using variations of cuboids and cubes 
    to resemble the detailed facades of reference images. The structure includes additional 
    details like windows, voids, and gutter details to create a non-flat facade.
    
    Parameters:
    - base_width (float): The width of the building base in meters.
    - base_depth (float): The depth of the building base in meters.
    - height (float): The total height of the building in meters.
    - detail_level (int): A level of detail parameter to control facade complexity.
    
    Returns:
    - List of Rhino.Geometry.Brep: The Brep objects representing the vertical structure.
    \"""
    import Rhino.Geometry as rg
    import random
    
    random.seed(42)

    # Main tower structure
    tower = rg.Box(rg.Plane.WorldXY, rg.Interval(0, base_width), rg.Interval(0, base_depth), rg.Interval(0, height))
    tower_brep = tower.ToBrep()

    # Create facade details
    facade_elements = []
    for i in range(detail_level):
        x_start = random.uniform(0, base_width - 1)
        y_start = random.uniform(0, base_depth - 1)
        detail_height = random.uniform(5, height / 3)

        detail_box = rg.Box(
            rg.Plane.WorldXY,
            rg.Interval(x_start, min(x_start + 1, base_width)),
            rg.Interval(y_start, min(y_start + 0.5, base_depth)),
            rg.Interval(0, detail_height)
        )
        
        detail_brep = detail_box.ToBrep()
        
        if detail_brep.IsValid:
            facade_elements.append(detail_brep)

    # Subtract facade elements from main tower for detailing
    detailed_tower = rg.Brep.CreateBooleanDifference([tower_brep], facade_elements, 0.001)
    detailed_tower = [b for b in detailed_tower if b.IsValid] if detailed_tower else [tower_brep]

    # Create window voids near the top
    windows = []
    window_height = height - 5
    window_width = base_width / 10
    for i in range(int(base_width // window_width)):
        window = rg.Box(
            rg.Plane.WorldXY,
            rg.Interval(i * window_width, min((i + 1) * window_width - 0.2, base_width)),
            rg.Interval(base_depth - 0.3, base_depth),
            rg.Interval(window_height, height - 0.5)
        )
        window_brep = window.ToBrep()
        
        if window_brep.IsValid:
            windows.append(window_brep)

    final_structure = rg.Brep.CreateBooleanDifference(detailed_tower, windows, 0.001)
    final_structure = [b for b in final_structure if b.IsValid] if final_structure else detailed_tower

    # Gutter details on the roof
    gutter_elements = []
    number_of_gutters = int(base_width // 2)
    gutter_width = base_width / number_of_gutters
    for i in range(number_of_gutters):
        gutter = rg.Box(
            rg.Plane.WorldXY,
            rg.Interval(i * gutter_width, min((i + 1) * gutter_width - 0.1, base_width)),
            rg.Interval(base_depth - 0.1, base_depth),
            rg.Interval(height - 0.2, height)
        )
        gutter_brep = gutter.ToBrep()
        
        if gutter_brep.IsValid:
            gutter_elements.append(gutter_brep)

    if gutter_elements:
        final_structure = rg.Brep.CreateBooleanUnion(final_structure + gutter_elements, 0.001)
        final_structure = [b for b in final_structure if b.IsValid] if final_structure else [tower_brep]
    
    return final_structure"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_vertical_structure(base_width=12, base_depth=8, height=60, detail_level=8)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_vertical_structure(base_width=8, base_depth=5, height=70, detail_level=7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_vertical_structure(base_width=14, base_depth=9, height=90, detail_level=12)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
