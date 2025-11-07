""" Summary:
The script builds an architectural façade by populating a 3D grid of cubic boxes whose sizes vary with their X and Y positions. It computes grid dimensions (user-specified or near-cubic to fit count), sets isotropic pitch from base_size and spacing, then normalizes X/Y indices (ux, uy). Each cube’s uniform scale = 1 + kx*ux + ky*uy, producing progressive sizing across the façade. Boxes are centered on a reference plane, constrained by document tolerance to avoid invalid Breps, converted to solid Breps, and collected. Three sample calls produce different arrays, which are packed into a Grasshopper DataTree for parametric facade control."""

#! python 3
function_code = """def generate_scaled_cubes(count=10, base_size=1.0, spacing=1.25, grid_dims=None, kx=0.6, ky=0.6, origin=None):
    \"""
    Generate a set of cubes arranged in a 3D grid, with each cube uniformly scaled
    based on its X and Y grid position. Ensures valid Breps by respecting document tolerance.
    \"""
    import math
    import Rhino
    import Rhino.Geometry as rg

    n = max(1, int(count))

    # Resolve reference plane
    if origin is None:
        base_plane = rg.Plane.WorldXY
    elif isinstance(origin, rg.Plane):
        base_plane = rg.Plane(origin)
    elif isinstance(origin, rg.Point3d):
        base_plane = rg.Plane(origin, rg.Vector3d.XAxis, rg.Vector3d.YAxis)
    else:
        base_plane = rg.Plane.WorldXY  # fallback

    if not base_plane.IsValid:
        base_plane = rg.Plane.WorldXY

    # Determine grid dimensions (nx, ny, nz)
    if grid_dims is not None and len(grid_dims) == 3:
        nx = max(1, int(grid_dims[0]))
        ny = max(1, int(grid_dims[1]))
        nz = max(1, int(grid_dims[2]))
        if nx * ny * nz < n:
            needed = int(math.ceil(float(n) / (nx * ny)))
            nz = max(nz, needed)
    else:
        # Near-cubic grid that can fit 'n' items
        cbrt = n ** (1.0 / 3.0)
        nx = int(math.ceil(cbrt))
        ny = max(1, nx)
        nz = int(math.ceil(float(n) / (nx * ny))) if (nx * ny) > 0 else 1

    # Center-to-center pitch in each axis (keep isotropic pitch for a cubic lattice)
    pitch = max(1e-6, float(base_size) * float(spacing))

    # Precompute normalizations for scaling (handle singleton dimensions)
    denom_x = float(nx - 1) if nx > 1 else 1.0
    denom_y = float(ny - 1) if ny > 1 else 1.0

    # Use document tolerance to avoid creating too-small (invalid) boxes
    tol = 0.001
    try:
        if Rhino.RhinoDoc.ActiveDoc:
            tol = max(1e-5, float(Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance))
    except:
        pass
    min_edge = 2.0 * tol

    breps = []
    made = 0
    for k in range(nz):
        if made >= n:
            break
        for j in range(ny):
            if made >= n:
                break
            for i in range(nx):
                if made >= n:
                    break

                # Normalized parameters along X and Y in [0,1] when nx, ny > 1
                ux = i / denom_x if denom_x > 0 else 0.0
                uy = j / denom_y if denom_y > 0 else 0.0

                # Uniform scale factor based on X and Y position in the grid
                scale = 1.0 + float(kx) * ux + float(ky) * uy
                edge = max(min_edge, float(base_size) * max(1e-9, scale))  # keep above tolerance

                # Center position in 3D using plane's axes (no 3-arg PointAt on Plane)
                cx = i * pitch
                cy = j * pitch
                cz = k * pitch
                center = (base_plane.Origin
                          + base_plane.XAxis * cx
                          + base_plane.YAxis * cy
                          + base_plane.ZAxis * cz)

                # Create a box centered on 'center' aligned to base_plane axes
                box_plane = rg.Plane(base_plane)
                box_plane.Origin = center

                half = 0.5 * edge
                xi = rg.Interval(-half, half)
                yi = rg.Interval(-half, half)
                zi = rg.Interval(-half, half)

                box = rg.Box(box_plane, xi, yi, zi)
                if not box.IsValid:
                    continue

                # Create Brep from box and validate
                brep = box.ToBrep()
                if brep and brep.IsSolid and brep.IsValid:
                    breps.append(brep)
                    made += 1

    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_scaled_cubes(count=27, base_size=1.5, spacing=1.2, grid_dims=(3,3,3), kx=0.5, ky=0.3, origin=None)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_scaled_cubes(count=64, base_size=0.5, spacing=1.1, grid_dims=None, kx=1.2, ky=0.8, origin=None)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_scaled_cubes(count=18, base_size=0.9, spacing=1.15, grid_dims=(3,3,2), kx=0.4, ky=0.9, origin=None)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
