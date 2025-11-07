""" Summary:
The script procedurally assembles a vertical tower of cubes by stacking grid arrays per level. Each level places cube centers on a centered XY grid sized by module and gap, then applies a rotation (twist per level) and an optional plan-wise sway. Alternating band offsets produce a Jenga-like shift; taper scales the grid toward the top. Porosity randomly removes cube positions with a seeded RNG for reproducibility. Cubes are created as Box primitives on local planes at each center and converted to Breps. Parameters (module, levels, grid, twist, shifts, porosity, taper, sway, seed) control the facade’s rhythm and void pattern."""

#! python 3
function_code = """def generate_cubic_tower(module=6.0,
                         levels=24,
                         grid_x=3,
                         grid_y=3,
                         gap=0.2,
                         twist_per_level_deg=5.0,
                         jenga_shift=1.0,
                         alternating=True,
                         porosity=0.1,
                         sway_amplitude=0.0,
                         sway_frequency=0.0,
                         taper=0.0,
                         seed=42):
    \"""
    Create a vertical tower composed of stacked cubes with optional twist, banded offsets (Jenga-like),
    porosity (removed cubes), taper, and global sway. Dimensions are in meters; Z is height.

    The tower is generated as a set of cube Breps arranged on a rotating XY grid per level. Each level can:
      - rotate around the Z-axis (twist),
      - shift alternating bands of cubes along X or Y (Jenga-like effect),
      - remove some cubes (porosity) using a seeded random generator,
      - taper toward the center as height increases,
      - sway along a sinusoidal path in plan as the tower rises.

    Inputs:
      - module (float): Edge length of each cube in meters. Also equals the vertical step per level. Default 6.0.
      - levels (int): Number of vertical layers of cubes. Default 24.
      - grid_x (int): Number of cubes per level along X (count in the grid). Default 3.
      - grid_y (int): Number of cubes per level along Y (count in the grid). Default 3.
      - gap (float): Clear spacing between cube centers in the grid beyond the cube size; controls facade porosity. Default 0.2.
      - twist_per_level_deg (float): Rotation in degrees applied per level about the Z-axis. Default 5.0.
      - jenga_shift (float): Magnitude of band offset (in meters) applied to alternating rows/columns per level. Default 1.0.
      - alternating (bool): If True, band direction alternates per level (X on even levels, Y on odd levels). Default True.
      - porosity (float): Probability [0..1) to remove a cube position (voids). Seeded for reproducibility. Default 0.1.
      - sway_amplitude (float): Amplitude (meters) of a plan-wise sway of the entire level. Default 0.0 (no sway).
      - sway_frequency (float): Radians per level controlling sway progression; e.g., 0.2 gives slow helix-like sway. Default 0.0.
      - taper (float): Linear taper factor [0..~0.95], shrinking grid toward center from base (0) to top (taper). Default 0.0.
      - seed (int): Random seed used for porosity. Default 42.

    Output:
      - list of Rhino.Geometry.Brep: The generated cube Breps forming the tower.

    Notes:
      - All geometry uses RhinoCommon; intended for Grasshopper's GhPython component in Rhino 8 (Python 3.9).
      - Set porosity to 0.0 for a solid pattern; set jenga_shift to 0.0 to disable band offsets; set twist to 0.0 for no rotation.
    \"""
    import math
    import random
    from Rhino.Geometry import Plane, Box, Interval, Vector3d, Point3d

    # Sanitize and prepare parameters
    levels = max(1, int(levels))
    grid_x = max(1, int(grid_x))
    grid_y = max(1, int(grid_y))
    s = float(module)
    gap = max(0.0, float(gap))
    porosity = max(0.0, min(0.999, float(porosity)))
    taper = max(0.0, min(0.95, float(taper)))
    twist_per_level_rad = math.radians(float(twist_per_level_deg))

    spacing = s + gap
    rng = random.Random(int(seed))

    breps = []

    # Precompute grid indices centered around origin in plane coordinates
    cx = (grid_x - 1) * 0.5
    cy = (grid_y - 1) * 0.5

    for i in range(levels):
        # Height at cube centers (each level is one cube tall)
        zc = (i + 0.5) * s

        # Plan rotation for this level
        theta = twist_per_level_rad * i

        # Optional plan-wise sway of the entire level (world XY)
        if sway_amplitude != 0.0 and sway_frequency != 0.0:
            dx = float(sway_amplitude) * math.sin(float(sway_frequency) * i)
            dy = float(sway_amplitude) * math.cos(float(sway_frequency) * i)
        else:
            dx = 0.0
            dy = 0.0

        # Construct the local plane of the level, rotated about Z at its centroid
        level_origin = Point3d(dx, dy, zc)
        level_plane = Plane(level_origin, Vector3d.XAxis, Vector3d.YAxis)
        level_plane.Rotate(theta, Vector3d(0, 0, 1), level_origin)

        # Determine Jenga band direction per level
        use_x_band = True if (not alternating or (i % 2 == 0)) else False

        # Linear taper factor toward the top (1.0 at base -> 1.0 - taper at top)
        if levels > 1:
            t = 1.0 - taper * (i / float(levels - 1))
        else:
            t = 1.0

        for ix in range(grid_x):
            for iy in range(grid_y):
                # Random removal based on porosity
                if porosity > 0.0 and rng.random() < porosity:
                    continue

                # Base grid coordinates in the level plane (centered at plane origin)
                u = (ix - cx) * spacing
                v = (iy - cy) * spacing

                # Apply Jenga-like band shift
                if jenga_shift != 0.0:
                    if use_x_band:
                        # Shift alternating rows along local X axis
                        sign = 1.0 if (iy % 2 == 0) else -1.0
                        u += sign * float(jenga_shift)
                    else:
                        # Shift alternating columns along local Y axis
                        sign = 1.0 if (ix % 2 == 0) else -1.0
                        v += sign * float(jenga_shift)

                # Apply taper scaling about the level's origin
                if t != 1.0:
                    u *= t
                    v *= t

                # Cube center in world coordinates
                center = level_plane.PointAt(u, v, 0.0)

                # Construct cube plane oriented like the level but at the cube center
                cube_plane = Plane(center, level_plane.XAxis, level_plane.YAxis)

                # Centered cube via symmetric intervals
                half = 0.5 * s
                iv = Interval(-half, half)
                cube = Box(cube_plane, iv, iv, iv)

                if cube.IsValid:
                    brep = cube.ToBrep()
                    if brep:
                        breps.append(brep)

    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_cubic_tower(module=2.5, levels=40, grid_x=3, grid_y=3, gap=0.05, twist_per_level_deg=4.0, jenga_shift=0.5, alternating=True, porosity=0.08, sway_amplitude=0.3, sway_frequency=0.25, taper=0.35, seed=123)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_cubic_tower(module=4.0, levels=36, grid_x=5, grid_y=5, gap=0.15, twist_per_level_deg=3.0, jenga_shift=0.6, alternating=False, porosity=0.12, sway_amplitude=0.4, sway_frequency=0.18, taper=0.45, seed=7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_cubic_tower(module=3.0, levels=28, grid_x=4, grid_y=2, gap=0.1, twist_per_level_deg=6.5, jenga_shift=0.8, alternating=True, porosity=0.15, sway_amplitude=0.25, sway_frequency=0.3, taper=0.25, seed=999)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
