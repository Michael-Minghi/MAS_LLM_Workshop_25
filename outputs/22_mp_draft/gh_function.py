""" Summary:
The script builds a vertical massing by stacking rectangular box segments along Z according to base_size, height and segment_height. For each segment it generates many small cuboidal facade details via create_facade_detail — thin linear boxes randomly offset across the face — and creates window/void boxes via create_voids. Details are boolean-unioned into the segment and voids are subtracted, producing non-flat facades with numerous small cubes, cuboids and gutters. A fixed random seed ensures repeatability. The function returns Rhino Breps per segment; the wrapper calls it with different parameters to produce three sample towers and converts results to a Grasshopper DataTree for visualization."""

#! python 3
function_code = """def generate_vertical_structure(base_size, height, segment_height, facade_detail_factor, void_size):
    \"""
    Generates a vertical architectural structure with detailed facades using numerous small cuboids and other shapes. 
    The function creates a detailed facade based on reference images to develop an intricate and structured form.
    
    Parameters:
    - base_size (tuple): A tuple of (width, depth) for the base dimensions in meters.
    - height (float): The overall height of the structure in meters.
    - segment_height (float): Height of each vertical segment in meters.
    - facade_detail_factor (int): Number of details per facade segment.
    - void_size (tuple): A tuple of (width, height) for voids/windows in meters.
    
    Returns:
    - list: A list of Rhino.Geometry.Brep representing the structure with detailed facades.
    \"""
    import Rhino.Geometry as rg
    import random

    random.seed(42)
    
    def create_facade_detail(base_plane, width, height, detail_factor):
        \"""Creates facade details using small linear rectangular cuboids.\"""
        details = []
        for i in range(detail_factor):
            x_offset = random.uniform(0, width - 0.1)
            z_offset = random.uniform(0, height - 0.1)
            detail_width = 0.1
            detail_height = random.uniform(0.5, 1.5)
            point = base_plane.Origin + rg.Vector3d(x_offset, 0, z_offset)
            detail = rg.Box(
                rg.Plane(point, base_plane.XAxis, base_plane.ZAxis),
                rg.Interval(0, detail_width),
                rg.Interval(0, 0.1),
                rg.Interval(0, detail_height)
            )
            details.append(detail.ToBrep())
        return details
    
    def create_voids(base_plane, width, depth, height, void_width, void_height):
        \"""Creates voids or windows on the facade.\"""
        voids = []
        spacing = (width - (void_width * 2)) / 3
        for i in range(2):
            x_offset = spacing + i * (void_width + spacing)
            z_offset = random.uniform(0, height - void_height)
            point = base_plane.Origin + rg.Vector3d(x_offset, depth / 2, z_offset)
            void = rg.Box(
                rg.Plane(point, base_plane.XAxis, base_plane.ZAxis),
                rg.Interval(0, void_width),
                rg.Interval(-0.05, 0.05),
                rg.Interval(0, void_height)
            )
            voids.append(void.ToBrep())
        return voids

    width, depth = base_size
    num_segments = int(height / segment_height)
    
    base_plane = rg.Plane.WorldXY
    geometries = []

    for i in range(num_segments):
        segment_base = base_plane.Clone()
        segment_base.Translate(rg.Vector3d(0, 0, i * segment_height))
        segment = rg.Box(
            segment_base,
            rg.Interval(0, width),
            rg.Interval(0, depth),
            rg.Interval(0, segment_height)
        )

        main_brep = segment.ToBrep()
        details = create_facade_detail(segment_base, width, segment_height, facade_detail_factor)
        voids = create_voids(segment_base, width, depth, segment_height, *void_size)

        # Union details with the main segment
        for detail in details:
            union_result = rg.Brep.CreateBooleanUnion([main_brep, detail], 0.01)
            if union_result:
                main_brep = union_result[0]

        # Subtract voids from the main segment
        for void in voids:
            diff_result = rg.Brep.CreateBooleanDifference([main_brep], [void], 0.01)
            if diff_result:
                main_brep = diff_result[0]

        geometries.append(main_brep)

    return geometries"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_vertical_structure((10, 4), 30, 3, 20, (1.2, 2.0))
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_vertical_structure((12, 5), 48, 3, 35, (1.0, 1.8))
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_vertical_structure((8, 3.5), 45, 2.5, 60, (0.9, 1.8))
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
