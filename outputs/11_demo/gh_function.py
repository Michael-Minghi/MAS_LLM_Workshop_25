""" Summary:
The script builds an architectural façade as a vertical tower of cube Breps by stacking oriented cubes along a helical path. It interpolates cube sizes (taper) and rotation (total twist) across n_levels, computes centered planes at incremental Z positions with consistent gaps, then offsets plane origins radially using cos/sin of the interpolated angle (radius) to create the helix. Each cube is created as a Box centered on its local plane using half-edge intervals, converted to a Brep, and appended to the output list. Parameters (cube_size, gap, radius, twist, taper) let designers control scale, spacing, rotation and massing."""

#! python 3
function_code = """def generate_cube_tower(n_levels=18, cube_size=3.0, gap=0.15, radius=2.0, total_twist_degrees=180.0, taper=1.0):
    \"""
    Generate a vertical tower structure composed of stacked cubes (as Breps), suitable for Grasshopper in Rhino 8.

    Concept
    - The tower is made by stacking cubes vertically with a controllable helical twist and radial offset.
    - Each cube can optionally taper in size from base to top while remaining a cube (uniform scaling).
    - The bottom of the first cube is aligned to Z=0. All dimensions are in meters.

    What it does
    - Computes a sequence of planes positioned along Z, rotated around the vertical axis according to a total twist.
    - Places a cube centered on each plane origin, oriented to the plane axes, and creates a Brep for each cube.
    - Ensures consistent vertical spacing by using cube sizes and a specified gap.

    Inputs
    - n_levels (int): Number of cubes stacked vertically (>=1).
    - cube_size (float): Base cube edge length in meters at the tower base.
    - gap (float): Vertical gap between adjacent cubes in meters.
    - radius (float): Horizontal radial offset from the Z-axis to the center of each cube (meters). 0 yields a straight stack.
    - total_twist_degrees (float): Total twist from base to top in degrees (e.g., 180 means the top cube has rotated 180° relative to the base).
    - taper (float): Multiplicative factor applied to the cube size at the top level; 1.0 = no taper, <1.0 = smaller at top, >1.0 = larger at top.

    Output
    - list[Rhino.Geometry.Brep]: A list of Breps, one for each cube in the tower, ordered from base to top.

    Notes
    - Uses only RhinoCommon (no rhinoscriptsyntax).
    - If n_levels == 1, there is no twist and no tapering interpolation (single cube at Z >= 0).
    \"""
    import math
    import Rhino
    from Rhino.Geometry import Plane, Vector3d, Point3d, Interval, Box

    # Validate inputs
    if n_levels is None or n_levels < 1:
        return []

    # Precompute interpolation denominator to avoid zero division
    denom = float(n_levels - 1) if n_levels > 1 else 1.0

    cubes = []

    # Prepare sequences of sizes, angles, and Z positions
    sizes = []
    angles_rad = []

    for i in range(n_levels):
        t = i / denom  # 0 at base, 1 at top
        # Linear taper from base size to top size (uniform scale to keep cubes)
        size_i = cube_size * (1.0 + (taper - 1.0) * t)
        sizes.append(size_i)
        # Twist interpolation
        angle_i = math.radians(total_twist_degrees) * t if n_levels > 1 else 0.0
        angles_rad.append(angle_i)

    # Compute Z positions to stack cubes with given gap; bottom at Z=0
    z_positions = []
    for i, size_i in enumerate(sizes):
        if i == 0:
            z_positions.append(size_i * 0.5)  # bottom flush with Z=0
        else:
            prev_size = sizes[i - 1]
            z_positions.append(z_positions[-1] + prev_size * 0.5 + gap + size_i * 0.5)

    # Build cube Breps
    for i in range(n_levels):
        size_i = sizes[i]
        angle_i = angles_rad[i]
        z_i = z_positions[i]

        # Center point in plan following a helical path
        cx = radius * math.cos(angle_i)
        cy = radius * math.sin(angle_i)
        center = Point3d(cx, cy, z_i)

        # Oriented plane (rotated about Z, then moved to center)
        p = Plane.WorldXY
        p = Plane(p)  # clone before mutation
        p.Rotate(angle_i, Vector3d.ZAxis, Point3d.Origin)
        p.Origin = center

        # Build a centered cube on the plane
        half = 0.5 * size_i
        ix = Interval(-half, half)
        iy = Interval(-half, half)
        iz = Interval(-half, half)

        box = Box(p, ix, iy, iz)
        brep = box.ToBrep()
        if brep:
            cubes.append(brep)

    return cubes"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_cube_tower(n_levels=24, cube_size=2.5, gap=0.1, radius=4.0, total_twist_degrees=360.0, taper=0.8)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_cube_tower(n_levels=20, cube_size=1.8, gap=0.12, radius=2.5, total_twist_degrees=270.0, taper=0.75)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_cube_tower(n_levels=12, cube_size=3.5, gap=0.2, radius=1.5, total_twist_degrees=90.0, taper=1.2)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
