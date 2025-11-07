""" Summary:
The script defines generate_scaled_cube_grid which arranges a specified number of cubes into rows and columns on an X–Y grid. For each cell it normalizes the column and row indices to [0,1], blends them with configurable x and y weights to compute t, and maps t into a scale between min_scale and max_scale. Each cube’s edge length equals base_size times that scale, and boxes are centered vertically so their bottoms sit at base_z. Spacing prevents overlap. Boxes are converted to Rhino Breps and returned; example calls create multiple facade variations and export them to a Grasshopper DataTree for parametric facade exploration."""

#! python 3
function_code = """def generate_scaled_cube_grid(count=10, cols=5, base_size=2.0, spacing=None, min_scale=0.6, max_scale=1.4, x_weight=1.0, y_weight=1.0, origin_x=0.0, origin_y=0.0, base_z=0.0):
    \"""
    Create a set of cubes arranged on a planar grid and scale each cube based on its x (column) and y (row) grid indices.

    Purpose:
        Generates up to 'count' cubes as Breps. The cubes are placed on a 2D grid (X-Y plane) with their bottoms on Z=base_z.
        Each cube's size is scaled between [min_scale, max_scale] according to its normalized grid position in x and y,
        optionally weighted by x_weight and y_weight.

    Operations:
        - Computes grid layout from total count and number of columns.
        - Normalizes each cube's (x,y) grid index to [0,1].
        - Computes a scale factor from the normalized indices and weights.
        - Creates a Box (cube) centered at an appropriate Z so it sits on the ground (base_z).
        - Converts Boxes to Breps and returns the list.

    Inputs:
        count (int): Total number of cubes to create. Default 10.
        cols (int): Number of columns in the grid (>=1). Rows are computed automatically. Default 5.
        base_size (float): Base cube edge length before scaling, in meters. Default 2.0.
        spacing (float or None): Center-to-center spacing between cubes in X and Y, in meters. If None,
                                 it is derived from base_size and max_scale to avoid overlap. Default None.
        min_scale (float): Minimum uniform scale factor per cube edge. Default 0.6.
        max_scale (float): Maximum uniform scale factor per cube edge. Default 1.4.
        x_weight (float): Weight of the x-position in the scaling calculation. Default 1.0.
        y_weight (float): Weight of the y-position in the scaling calculation. Default 1.0.
        origin_x (float): World X coordinate of the grid origin (lower-left cell center in plan). Default 0.0.
        origin_y (float): World Y coordinate of the grid origin. Default 0.0.
        base_z (float): Elevation (in meters) where cube bottoms sit. Default 0.0.

    Outputs:
        list[Rhino.Geometry.Brep]: A list of Breps representing the scaled cubes.

    Notes:
        - All dimensions are in meters. Z is height, X is width, Y is depth.
        - Uses RhinoCommon only (no rhinoscriptsyntax).
    \"""
    import math
    import Rhino

    # Basic guards and parameter sanitation
    count = max(0, int(count))
    cols = max(1, int(cols))
    min_scale = float(min_scale)
    max_scale = float(max_scale)

    if count == 0:
        return []

    if min_scale <= 0:
        min_scale = 0.001  # avoid zero/negative sizes
    if max_scale < min_scale:
        min_scale, max_scale = max_scale, min_scale  # swap if provided in reverse

    # Determine rows based on count and columns
    rows = int(math.ceil(float(count) / float(cols)))

    # Derive spacing if not provided: ensure no overlap at max scale
    if spacing is None or spacing <= 0:
        spacing = base_size * max_scale * 1.2  # a bit of clearance

    # Precompute denominator for weighted normalization
    weight_sum = float(x_weight + y_weight)
    if weight_sum == 0.0:
        # If both weights are zero, fallback to equal influence
        xw = yw = 1.0
        weight_sum = 2.0
    else:
        xw, yw = float(x_weight), float(y_weight)

    breps = []
    for i in range(count):
        r = i // cols
        c = i % cols

        # Normalized grid positions in [0,1]
        nx = float(c) / float(cols - 1) if cols > 1 else 0.0
        ny = float(r) / float(rows - 1) if rows > 1 else 0.0

        # Blend normalized positions with weights
        t = (xw * nx + yw * ny) / weight_sum
        # Map to scale range
        s = min_scale + t * (max_scale - min_scale)

        # Compute cube size and placement
        size = base_size * s
        half = 0.5 * size

        cx = origin_x + c * spacing
        cy = origin_y + r * spacing
        cz = base_z + half  # set bottom at base_z

        # Construct a box (cube) centered at (cx, cy, cz)
        plane = Rhino.Geometry.Plane.WorldXY
        plane.Origin = Rhino.Geometry.Point3d(cx, cy, cz)
        x_int = Rhino.Geometry.Interval(-half, half)
        y_int = Rhino.Geometry.Interval(-half, half)
        z_int = Rhino.Geometry.Interval(-half, half)

        box = Rhino.Geometry.Box(plane, x_int, y_int, z_int)
        brep = box.ToBrep()
        if brep:
            breps.append(brep)

    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_scaled_cube_grid(count=30, cols=6, base_size=1.2, spacing=None, min_scale=0.5, max_scale=1.8, x_weight=1.5, y_weight=0.5, origin_x=-3.0, origin_y=-2.0, base_z=0.0)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_scaled_cube_grid(count=16, cols=4, base_size=0.8, spacing=1.5, min_scale=0.4, max_scale=2.0, x_weight=0.3, y_weight=1.7, origin_x=1.0, origin_y=1.0, base_z=0.2)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_scaled_cube_grid(count=25, cols=5, base_size=1.0, spacing=1.4, min_scale=0.6, max_scale=1.6, x_weight=2.0, y_weight=0.5, origin_x=-2.0, origin_y=-2.0, base_z=0.0)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
