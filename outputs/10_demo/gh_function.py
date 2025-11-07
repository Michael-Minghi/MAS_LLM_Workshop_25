""" Summary:
The script procedurally builds a vertical tower of cubes by stacking cubic modules along Z. For each level it interpolates cube size from a base module to a top_scale, computes center heights ensuring a consistent vertical gap, and positions plan coordinates on a circular helix using a radius and per-level rotation angle. Each cube is created as a RhinoCommon box Brep, translated to its helical center and optionally rotated about its own center. The function returns a list of Breps for visualization or operations. Multiple sample parameter sets demonstrate varied taper, twist, spacing, and orbital offset to match the reference."""

#! python 3
function_code = """def generate_cube_tower(levels=12, module=6.0, gap=0.4, rotation_step_deg=15.0, radius=3.0, top_scale=0.8, rotate_cubes=True):
    \"""
    Generate a vertical tower structure composed of stacked cubes, following a helical offset and optional twist.
    
    Purpose:
        Creates a parametric 3D tower made of cubic modules that ascend along Z, optionally tapering toward the top,
        rotating by a fixed increment per level, and orbiting a central axis at a given radius. This captures the
        character of a vertical tower of cubes similar to common reference images of twisting, offset cube stacks.
    
    What it does:
        - Computes a cubic module size for each level via linear interpolation from the base size to the top size.
        - Places each cube so that there is a consistent vertical gap between successive cubes.
        - Offsets cube centers in plan along a helical path with a specified radius.
        - Optionally rotates each cube about its own center by a fixed angle increment per level.
        - Returns the cubes as individual Breps suitable for further boolean operations or direct display.
    
    Inputs:
        levels (int): Number of cubes stacked along Z. Must be >= 1.
        module (float): Base cube edge length in meters (edge size at the base level). Must be > 0.
        gap (float): Vertical clear distance (in meters) between successive cubes. Must be >= 0.
        rotation_step_deg (float): Per-level rotation in degrees applied about the Z axis. Can be any float.
        radius (float): Planar offset radius (in meters) from the tower axis to each cube center. Must be >= 0.
        top_scale (float): Scale factor for the top cube relative to the base cube (1.0 = uniform, <1.0 = taper).
                           Must be > 0.
        rotate_cubes (bool): If True, each cube is rotated about its center by rotation_step_deg per level;
                             if False, cubes remain axis-aligned while their centers follow the helix.
    
    Outputs:
        list of Rhino.Geometry.Brep: A list of Breps, each representing a cube in the tower.
    
    Notes:
        - Units are meters; Z is vertical height, X is width, Y is depth.
        - Uses RhinoCommon only (no rhinoscriptsyntax).
    \"""
    import math
    import Rhino.Geometry as rg

    # Sanitize and guard parameters
    try:
        levels = int(levels)
    except:
        levels = 0
    if levels < 1:
        return []
    module = float(module)
    if module <= 0:
        module = 1.0
    gap = max(0.0, float(gap))
    radius = max(0.0, float(radius))
    top_scale = float(top_scale)
    if top_scale <= 0:
        top_scale = 1.0
    rotation_step_rad = math.radians(float(rotation_step_deg))

    # Precompute cube sizes per level with linear interpolation from base to top
    sizes = []
    if levels == 1:
        sizes = [module * top_scale]  # single cube at top scale for consistency
    else:
        for i in range(levels):
            t = float(i) / float(levels - 1)  # 0 at base, 1 at top
            size = module * ((1.0 - t) + t * top_scale)
            sizes.append(size)

    # Compute center Z for each cube so the vertical gap is exact between consecutive cubes
    centers_z = []
    z_cursor = 0.0
    for s in sizes:
        center_z = z_cursor + 0.5 * s
        centers_z.append(center_z)
        z_cursor += s + gap

    breps = []
    world_origin = rg.Point3d(0.0, 0.0, 0.0)

    for i, sz in enumerate(sizes):
        angle = i * rotation_step_rad
        # Helical plan position
        cx = radius * math.cos(angle)
        cy = radius * math.sin(angle)
        cz = centers_z[i]
        center = rg.Point3d(cx, cy, cz)

        # Create a cube centered at the origin
        half = 0.5 * sz
        box = rg.Box(rg.Plane.WorldXY,
                     rg.Interval(-half, half),
                     rg.Interval(-half, half),
                     rg.Interval(-half, half))
        cube_brep = box.ToBrep()

        # Move cube to its center
        to_center = rg.Transform.Translation(center - world_origin)
        cube_brep.Transform(to_center)

        # Optional per-level rotation about its own center around Z
        if rotate_cubes and rotation_step_rad != 0.0:
            rot = rg.Transform.Rotation(angle, rg.Vector3d.ZAxis, center)
            cube_brep.Transform(rot)

        breps.append(cube_brep)

    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_cube_tower(levels=16, module=5.0, gap=0.3, rotation_step_deg=22.5, radius=4.0, top_scale=0.6, rotate_cubes=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_cube_tower(levels=10, module=4.0, gap=0.2, rotation_step_deg=30.0, radius=2.5, top_scale=0.9, rotate_cubes=False)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_cube_tower(levels=20, module=3.5, gap=0.5, rotation_step_deg=10.0, radius=1.5, top_scale=0.5, rotate_cubes=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
