""" Summary:
The script builds a parametric facade by populating a 3D grid of axis-aligned cube Breps and scaling each cube by its normalized X–Y position. Grid dimensions (nx, ny, nz), total count, base_size and spacing define layout; centered/ origin controls placement. For each grid cell it computes nx_norm and ny_norm in [0,1], blends them to t, interpolates s between scale_min and scale_max, and scales base_size. Cube centers are computed from origin, offset and step, boxes are created around each center and converted to Breps. The function returns up to count cubes, producing a gradient of sizes across the facade, creating rhythm."""

#! python 3
function_code = """def generate_scaled_cubes(count=10, nx=5, ny=2, nz=1, base_size=1.0, spacing=1.25, scale_min=0.5, scale_max=1.2, origin=None, centered=True):
    \"""
    Generate a set of cubes arranged in a 3D grid and scaled based on their x and y grid position.

    Purpose:
        Creates a parametric array of cubes (as Breps) positioned in a 3D grid. Each cube's size is scaled
        according to its normalized x and y position in the grid, producing a gradient effect across the array.

    What it does:
        - Lays out cubes on a 3D grid defined by nx, ny, nz.
        - Scales each cube using a factor interpolated between scale_min and scale_max based on its x and y index.
        - Returns up to 'count' cubes, enabling the default to generate exactly 10 cubes with nx=5, ny=2, nz=1.

    Inputs:
        - count (int): Total number of cubes to generate. Default is 10.
        - nx, ny, nz (ints): Grid dimensions along X, Y, Z. Default 5x2x1.
        - base_size (float): Base edge length of an unscaled cube (meters). Default 1.0.
        - spacing (float): Multiplier for center-to-center spacing relative to base_size. Default 1.25.
                           Effective step = base_size * spacing.
        - scale_min (float): Minimum scale factor for cube size. Default 0.5.
        - scale_max (float): Maximum scale factor for cube size. Default 1.2.
        - origin (Point3d or None): Origin point for the grid. If None, uses (0,0,0).
        - centered (bool): If True, centers the entire grid around the origin; otherwise starts at origin. Default True.

    Outputs:
        - List of Rhino.Geometry.Brep: Breps representing the cubes.

    Notes:
        - Uses RhinoCommon only; no randomness.
        - Dimensions are in meters; Z is vertical.
        - If nx*ny*nz < count, the function returns nx*ny*nz cubes (the maximum possible).
    \"""
    import Rhino
    import Rhino.Geometry as rg

    # Validate and setup
    if nx < 1 or ny < 1 or nz < 1:
        return []
    if count < 1:
        return []

    if origin is None:
        origin = rg.Point3d(0.0, 0.0, 0.0)

    # Compute grid stepping
    step = base_size * spacing

    # Optionally center the entire grid around the origin
    if centered:
        offset = rg.Vector3d(-(nx - 1) * step * 0.5, -(ny - 1) * step * 0.5, -(nz - 1) * step * 0.5)
    else:
        offset = rg.Vector3d(0.0, 0.0, 0.0)

    # Normalization denominators for scaling based on x/y position
    dx = float(nx - 1) if nx > 1 else 1.0
    dy = float(ny - 1) if ny > 1 else 1.0

    cubes = []
    total_available = nx * ny * nz
    target = min(count, total_available)

    # Build cubes across the grid
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if len(cubes) >= target:
                    break

                # Compute normalized positions in x and y [0..1]
                nx_norm = i / dx if dx > 0 else 0.0
                ny_norm = j / dy if dy > 0 else 0.0

                # Scale factor blends x and y influence equally
                t = 0.5 * (nx_norm + ny_norm)
                s = scale_min + (scale_max - scale_min) * t
                cube_size = max(0.0, base_size * s)

                # Center position of this cube
                cx = origin.X + offset.X + i * step
                cy = origin.Y + offset.Y + j * step
                cz = origin.Z + offset.Z + k * step
                center = rg.Point3d(cx, cy, cz)

                # Create centered box (cube) aligned to World XY
                plane = rg.Plane(center, rg.Vector3d.XAxis, rg.Vector3d.YAxis)
                half = cube_size * 0.5
                interval = rg.Interval(-half, half)
                box = rg.Box(plane, interval, interval, interval)

                brep = box.ToBrep()
                if brep:
                    cubes.append(brep)

            if len(cubes) >= target:
                break
        if len(cubes) >= target:
            break

    return cubes"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_scaled_cubes(count=30, nx=6, ny=5, nz=2, base_size=0.6, spacing=1.2, scale_min=0.5, scale_max=1.4, origin=None, centered=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_scaled_cubes(count=12, nx=4, ny=3, nz=2, base_size=0.8, spacing=1.15, scale_min=0.4, scale_max=1.6, origin=None, centered=False)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_scaled_cubes(count=15, nx=5, ny=3, nz=1, base_size=0.9, spacing=1.1, scale_min=0.6, scale_max=1.8, origin=None, centered=False)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
