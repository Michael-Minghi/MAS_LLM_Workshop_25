""" Summary:
The script creates a façade by arranging a grid of cubes whose sizes depend on their normalized X–Y positions and stack vertically. It maps each index to a grid column and row, computes normalized u and v, then interpolates a scale between scale_min and scale_max using average of u and v. Cube edge = base_size*scale; planar X/Y are centered around origin with given spacing. Cubes are created as Rhino Box Breps with Z extents set by a cumulative elevation that increments by each cube’s height plus vertical_gap, yielding a piled-up stack. Parameters control count, grid, spacing, scaling, and origin positioning."""

#! python 3
function_code = """def generate_scaled_piled_cubes(count=10, grid_cols=5, grid_rows=2, base_size=1.0, spacing=1.5, scale_min=0.6, scale_max=1.4, vertical_gap=0.0, origin=None):
    \"""
    Generate a gridded structure of cubes that pile up along the Z axis.
    
    The function creates 'count' cubes (default 10) whose plan positions follow a rectangular
    grid in X and Y, while their sizes (uniform in X, Y, Z) are scaled according to their
    grid coordinates. The cubes are placed sequentially on top of each other along Z
    (i.e., they "pile up"), with the base elevation of each cube equal to the cumulative
    height of all previous cubes plus an optional vertical gap.
    
    Operations use RhinoCommon and dimensions are in meters.
    
    Inputs:
    - count (int): Number of cubes to generate. Default 10.
    - grid_cols (int): Number of grid columns in X. Default 5.
    - grid_rows (int): Number of grid rows in Y. Default 2.
    - base_size (float): Base edge length for cubes (before scaling). Default 1.0 m.
    - spacing (float): Center-to-center spacing between grid points in X and Y. Default 1.5 m.
    - scale_min (float): Minimum scale factor for cube size based on grid position. Default 0.6.
    - scale_max (float): Maximum scale factor for cube size based on grid position. Default 1.4.
    - vertical_gap (float): Optional gap between stacked cubes along Z. Default 0.0 m.
    - origin (Rhino.Geometry.Point3d or None): World origin for the structure. If None, uses (0,0,0).
    
    Scaling logic:
    - Each cube's scale factor is derived from its normalized column (u) and row (v) positions:
      scale = scale_min + (scale_max - scale_min) * 0.5 * (u + v),
      where u and v are in [0,1] across the grid extents.
    
    Output:
    - List[Rhino.Geometry.Brep]: A list of cube Breps.
    \"""
    import Rhino.Geometry as rg

    # Validate and sanitize inputs
    count = max(1, int(count))
    grid_cols = max(1, int(grid_cols))
    grid_rows = max(1, int(grid_rows))
    base_size = float(base_size)
    spacing = float(spacing)
    vertical_gap = float(vertical_gap)
    smin = float(scale_min)
    smax = float(scale_max)
    if smin > smax:
        smin, smax = smax, smin

    if origin is None:
        origin = rg.Point3d(0.0, 0.0, 0.0)
    elif not isinstance(origin, rg.Point3d):
        # Try to interpret as iterable of three values
        try:
            ox, oy, oz = origin
            origin = rg.Point3d(float(ox), float(oy), float(oz))
        except:
            origin = rg.Point3d(0.0, 0.0, 0.0)

    # Denominators for normalization across grid (avoid division by zero)
    u_den = float(max(grid_cols - 1, 1))
    v_den = float(max(grid_rows - 1, 1))

    results = []
    cum_z = origin.Z  # current stacking elevation

    for i in range(count):
        # Map index to grid coordinates (wrap rows if count exceeds grid capacity)
        col = i % grid_cols
        row = (i // grid_cols) % grid_rows

        # Normalized positions across the grid extents
        u = col / u_den
        v = row / v_den

        # Scale factor based on grid position (average of u and v)
        scale = smin + (smax - smin) * 0.5 * (u + v)

        # Cube size (edge length)
        size = base_size * scale

        # Planar position centered around origin
        x = origin.X + (col - 0.5 * (grid_cols - 1)) * spacing
        y = origin.Y + (row - 0.5 * (grid_rows - 1)) * spacing

        # Vertical placement (pile up)
        z0 = cum_z
        z1 = z0 + size

        # Define box extents around the plan position
        x0, x1 = x - 0.5 * size, x + 0.5 * size
        y0, y1 = y - 0.5 * size, y + 0.5 * size

        box = rg.Box(rg.Plane.WorldXY, rg.Interval(x0, x1), rg.Interval(y0, y1), rg.Interval(z0, z1))
        brep = box.ToBrep()
        if brep:
            results.append(brep)

        # Update cumulative height for next cube
        cum_z = z1 + vertical_gap

    return results"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_scaled_piled_cubes(count=12, grid_cols=4, grid_rows=3, base_size=0.8, spacing=1.2, scale_min=0.5, scale_max=1.8, vertical_gap=0.05, origin=(2.0, 3.0, 0.0))
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_scaled_piled_cubes(count=18, grid_cols=6, grid_rows=3, base_size=0.75, spacing=1.25, scale_min=0.4, scale_max=1.6, vertical_gap=0.02, origin=(0.0, 0.0, 0.0))
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_scaled_piled_cubes(count=20, grid_cols=5, grid_rows=4, base_size=0.9, spacing=1.0, scale_min=0.7, scale_max=1.3, vertical_gap=0.1, origin=(0.5, -1.0, 0.0))
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
