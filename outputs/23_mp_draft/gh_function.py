""" Summary:
The script builds a vertical building by creating a base box sized to the given width, depth, and height, then adds numerous small cuboid detail elements across its surfaces. For each detail, randomized x/y/z positions and dimensions produce many small cuboids and linear rectangular geometries with two orientation variants, creating horizontal and vertical segments. It then carves out multiple voids/windows by subtracting thin box volumes from recent geometry to break the facade plane. Random seeds ensure repeatable variations and multiple sample runs produce different façades. Resulting Rhino Brep objects are collected and exported as a Grasshopper DataTree for visualization output."""

#! python 3
function_code = """def create_vertical_structure(base_size, height, detail_count, seed=42):
    \"""
    Generates a vertical architectural structure with detailed facades using numerous small cuboids and linear elements.
    
    Parameters:
    - base_size: tuple of (width, depth). Base size of the building in meters.
    - height: float. Total height of the building in meters.
    - detail_count: int. Number of detail elements to add on the facades and roof.
    - seed: int. Random seed for replicable results.
    
    Returns:
    - List of Breps representing the generated architectural structure.
    \"""
    import Rhino.Geometry as rg
    import random
    
    random.seed(seed)
    
    width, depth = base_size
    base = rg.Box(rg.Plane.WorldXY, rg.Interval(0, width), rg.Interval(0, depth), rg.Interval(0, height))
    
    breps = [base.ToBrep()]
    
    # Create facade details
    for _ in range(detail_count):
        x_pos = random.uniform(0, width)
        y_pos = random.uniform(0, depth)
        z_pos = random.uniform(0, height)
        
        detail_width = random.uniform(0.2, 0.4)  # Random width between 0.2 and 0.4 meters
        detail_height = random.uniform(1, 3)  # Random height between 1 and 3 meters
        detail_depth = random.uniform(0.1, 0.2)  # Random depth between 0.1 and 0.2 meters
        
        if random.choice([True, False]):
            detail = rg.Box(
                rg.Plane.WorldXY,
                rg.Interval(max(0, min(x_pos, width - detail_width)), max(0, min(x_pos + detail_width, width))),
                rg.Interval(max(0, min(y_pos, depth - detail_depth)), max(0, min(y_pos + detail_depth, depth))),
                rg.Interval(max(0, min(z_pos, height - detail_height)), max(0, min(z_pos + detail_height, height)))
            )
        else:
            detail = rg.Box(
                rg.Plane.WorldXY,
                rg.Interval(max(0, min(x_pos, width - detail_depth)), max(0, min(x_pos + detail_depth, width))),
                rg.Interval(max(0, min(y_pos, depth - detail_width)), max(0, min(y_pos + detail_width, depth))),
                rg.Interval(max(0, min(z_pos, height - detail_height)), max(0, min(z_pos + detail_height, height)))
            )
        
        breps.append(detail.ToBrep())
    
    # Subtract voids and windows for non-flat facades
    for _ in range(int(detail_count / 4)):
        x_pos = random.uniform(0, width)
        y_pos = random.uniform(0, depth)
        z_pos = random.uniform(0, height)
        
        void_width = random.uniform(0.5, 1.5)  # Random void width between 0.5 and 1.5 meters
        void_height = random.uniform(1, 2)  # Random void height between 1 and 2 meters
        void_depth = 0.1  # Small fixed depth for voids/windows
        
        void = rg.Box(
            rg.Plane.WorldXY,
            rg.Interval(max(0, min(x_pos, width - void_width)), max(0, min(x_pos + void_width, width))),
            rg.Interval(max(0, min(y_pos, depth - void_depth)), max(0, min(y_pos + void_depth, depth))),
            rg.Interval(max(0, min(z_pos, height - void_height)), max(0, min(z_pos + void_height, height)))
        )
        
        diff_result = rg.Brep.CreateBooleanDifference([breps[-1]], [void.ToBrep()], 0.01)
        if diff_result:
            breps[-1] = diff_result[0]
    
    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = create_vertical_structure((10, 6), 45.0, 120, seed=99)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = create_vertical_structure((12, 8), 60.0, 200, seed=7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = create_vertical_structure((8, 5), 30.0, 80, seed=123)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
