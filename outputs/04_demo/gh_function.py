""" Summary:
The script builds a vertical tower of cube modules by stacking cubic Breps on a 2D integer grid per level. Parameters control cube size, grid extent, levels, footprint shape (square/plus/circle), arm width, tapering of the grid toward the top, per-level twist and XY shift, and gap between cubes. For each level it computes a tapered integer footprint, applies deterministic porosity (seeded RNG) to remove modules, then rotates/translates cell centers and places oriented Boxes at the level plane. The result is a parametric, repeatable façade/volume composed of cubes exported as Rhino Breps and organized into a Grasshopper DataTree for procedural design."""

#! python 3
function_code = """def generate_cubic_tower(module=3.0,
                         levels=24,
                         grid_size=(7, 7),
                         footprint='plus',
                         arm_width=1,
                         taper=0.4,
                         twist_deg_per_level=3.0,
                         shift_per_level=(0.0, 0.0),
                         gap=0.0,
                         porosity=0.0,
                         seed=1):
    \"""
    Generate a vertical tower structure composed of cubic modules (as Breps), suitable for Grasshopper Python in Rhino 8.

    Concept:
        Builds a parametric tower by stacking cubic modules on a 2D grid. Each level can rotate (twist), translate (shift),
        and taper (reduce footprint) with height. The footprint can be square, plus-shaped, or circular. Optional porosity
        removes modules deterministically to create voids/windows. Dimensions are in meters. Z is height, X is width, Y is depth.

    Parameters:
        module (float): Edge length of each cube in meters (also the floor-to-floor height).
        levels (int): Number of vertical layers.
        grid_size (tuple(int, int)): Base grid size (nx, ny) in number of cubes. Will auto-adjust to odd numbers for symmetry.
        footprint (str): Footprint type per level. Options: 'square', 'plus', 'circle'.
        arm_width (int): For 'plus' footprint, half-width of arms in grid cells (>=0). Ignored for other footprints.
        taper (float): 0..1 factor controlling how much the footprint shrinks towards the top (0=no taper, 1=to a single core).
        twist_deg_per_level (float): Rotation in degrees applied per level around the Z axis.
        shift_per_level (tuple(float, float)): XY translation per level in meters (world coordinates).
        gap (float): Spacing between adjacent cubes in meters (added to module when laying out grid).
        porosity (float): 0..1 probability to remove a cube (void). Uses a seeded RNG for repeatability. 0 disables removal.
        seed (int): Seed for deterministic porosity pattern.

    Returns:
        list[Rhino.Geometry.Brep]: A list of Breps, each representing a cube in the tower.
    \"""
    import math
    import random
    import Rhino.Geometry as rg

    # Validate and normalize inputs
    nx, ny = max(1, int(grid_size[0])), max(1, int(grid_size[1]))
    # Ensure odd counts for symmetry around origin
    if nx % 2 == 0:
        nx -= 1
    if ny % 2 == 0:
        ny -= 1
    nx = max(1, nx)
    ny = max(1, ny)

    levels = max(1, int(levels))
    module = max(1e-6, float(module))
    gap = max(0.0, float(gap))
    arm_width = max(0, int(arm_width))
    taper = max(0.0, min(1.0, float(taper)))
    porosity = max(0.0, min(1.0, float(porosity)))
    sx, sy = float(shift_per_level[0]), float(shift_per_level[1])

    # Precompute grid extents
    rx_max = (nx - 1) // 2  # integer half-range in x
    ry_max = (ny - 1) // 2  # integer half-range in y
    # For circular footprint radius
    r_max = math.hypot(rx_max, ry_max)

    # Prepare geometry containers and constants
    out_breps = []
    step = module + gap
    twist_rad_per_level = math.radians(float(twist_deg_per_level))

    # Pre-create cube intervals (centered at the plane origin)
    half = module * 0.5
    xint = rg.Interval(-half, half)
    yint = rg.Interval(-half, half)
    zint = rg.Interval(-half, half)

    # Helper functions for footprint checks
    def in_square(ix, iy, arx, ary):
        return abs(ix) <= arx and abs(iy) <= ary

    def in_plus(ix, iy, arx, ary, aw):
        # Plus shape with arm half-width aw, clipped by available ranges arx, ary
        return (abs(ix) <= aw or abs(iy) <= aw) and abs(ix) <= arx and abs(iy) <= ary

    def in_circle(ix, iy, fr):
        # Within circular radius scaled by taper factor
        if r_max <= 0:
            return True
        return math.hypot(ix, iy) <= fr * r_max + 1e-9

    # Iterate levels
    for k in range(levels):
        t = 0.0 if levels == 1 else float(k) / float(levels - 1)
        # Taper factor towards top
        f = 1.0 - taper * t
        # Allowed integer extents per level (at least core of 0)
        arx = max(0, int(round(rx_max * f)))
        ary = max(0, int(round(ry_max * f)))

        # Transforms for this level: rotation then translation
        angle = twist_rad_per_level * k
        rot = rg.Transform.Rotation(angle, rg.Vector3d(0, 0, 1), rg.Point3d(0, 0, 0))
        tr = rg.Transform.Translation(sx * k, sy * k, 0.0)
        T = tr * rot  # apply rotation then translation

        # Orientation plane for cubes on this level
        level_plane = rg.Plane.WorldXY
        level_plane.Rotate(angle, rg.Vector3d(0, 0, 1), rg.Point3d(0, 0, 0))

        # Iterate grid cells
        for ix in range(-rx_max, rx_max + 1):
            for iy in range(-ry_max, ry_max + 1):
                # Footprint inclusion
                include = False
                if footprint == 'square':
                    include = in_square(ix, iy, arx, ary)
                elif footprint == 'circle':
                    include = in_circle(ix, iy, f)
                else:
                    # default to plus
                    include = in_plus(ix, iy, arx, ary, arm_width)

                if not include:
                    continue

                # Porosity-based removal (deterministic)
                if porosity > 0.0:
                    rng = random.Random(seed + 1009 * k + 917 * ix + 463 * iy)
                    if rng.random() < porosity:
                        continue

                # Local center before transform
                cx_local = ix * step
                cy_local = iy * step
                cz = k * module + half

                # Apply rotation and shift per level in XY
                p = rg.Point3d(cx_local, cy_local, 0.0)
                p.Transform(T)
                center = rg.Point3d(p.X, p.Y, cz)

                # Build cube as a Box oriented by level_plane at 'center'
                cube_plane = rg.Plane(level_plane)
                cube_plane.Origin = center

                box = rg.Box(cube_plane, xint, yint, zint)
                brep = box.ToBrep()
                if brep:
                    out_breps.append(brep)

    return out_breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_cubic_tower(module=2.0, levels=40, grid_size=(11, 11), footprint='plus', arm_width=1, taper=0.7, twist_deg_per_level=4.5, shift_per_level=(0.02, 0.02), gap=0.05, porosity=0.12, seed=123)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_cubic_tower(module=1.25, levels=60, grid_size=(9, 9), footprint='circle', taper=0.85, twist_deg_per_level=2.5, shift_per_level=(0.01, -0.01), gap=0.02, porosity=0.08, seed=42)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_cubic_tower(module=1.5, levels=30, grid_size=(13, 13), footprint='square', taper=0.5, twist_deg_per_level=6.0, shift_per_level=(0.05, 0.0), gap=0.08, porosity=0.18, seed=7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
