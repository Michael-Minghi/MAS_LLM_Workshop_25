""" Summary:
The script builds a cubicle facade by creating a solid box and subdividing it into an nx×ny×nz grid. It carves internal void boxes offset by wall thickness to produce walls and a continuous outer shell. Parametric rules then place rectangular opening boxes on interior partitions and perimeter faces according to selectable patterns (checker, random, grid, cross, ring) and density/seed options; vertical openings between floors are optional. Opening sizes derive from opening_ratio and opening_height_ratio. All voids and openings are subtracted from the mass with Rhino boolean differences, yielding Brep walls. Sample calls produce variants and export geometry as a Grasshopper DataTree."""

#! python 3
function_code = """def create_cubicle_structure(length=12.0, depth=12.0, height=6.0,
                             nx=3, ny=3, nz=2,
                             wall_thickness=0.2,
                             opening_ratio=0.6,
                             opening_height_ratio=0.6,
                             pattern='checker',
                             open_density=0.5,
                             add_vertical_openings=False,
                             seed=42):
    \"""
    Create a modular cubicle structure with wall openings suitable for architectural massing.
    
    Concept:
        - The space is subdivided into a 3D grid of cubicles.
        - A single outer mass is carved by internal "void boxes" to form individual cubicles with consistent wall thickness.
        - Rectangular openings are then subtracted at selected partition walls (and optionally perimeter) to create porosity.
        - Openings align to a parametric pattern (checker, random, grid, cross, ring).
    
    Parameters (units in meters):
        length, depth, height (float): Overall extents of the structure along X, Y, Z respectively.
        nx, ny, nz (int): Number of cubicles along X, Y, Z (grid resolution).
        wall_thickness (float): Target thickness for interior partitions and outer shell.
        opening_ratio (float 0-1): Width ratio of openings relative to a cubicle's inner span (lateral).
        opening_height_ratio (float 0-1): Height ratio of openings relative to a cubicle's inner height.
        pattern (str): Opening layout pattern across walls. Options:
            - 'checker' (default): Alternating openings across the grid.
            - 'random': Openings distributed by probability (see open_density).
            - 'grid': Every other partition in X and Y.
            - 'cross': Openings along center rows/columns (per floor).
            - 'ring': Openings along perimeter bands.
        open_density (float 0-1): Probability for opening placement in 'random' pattern.
        add_vertical_openings (bool): If True, creates openings between stacked cubicles (Z partitions) as well.
        seed (int): Random seed for deterministic patterns when 'random' is used.
    
    Returns:
        list of Rhino.Geometry.Brep:
            The resulting breps form the solid structure (walls) with subtracted voids and openings.
            The list typically contains a single Brep, but may include multiple if the result is disjoint.
    \"""
    import Rhino
    from Rhino.Geometry import Point3d, Interval, Plane, Box, Brep
    import random
    tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance if Rhino.RhinoDoc.ActiveDoc else 1e-6

    # Basic guards and derived measures
    nx = max(1, int(nx)); ny = max(1, int(ny)); nz = max(1, int(nz))
    length = float(max(0.1, length)); depth = float(max(0.1, depth)); height = float(max(0.1, height))
    cx = length / nx; cy = depth / ny; cz = height / nz
    min_cell = min(cx, cy, cz)
    # Clamp wall thickness to avoid degeneracy; interior walls are centered on partitions, outer shell full thickness
    t = max(0.01, min(wall_thickness, 0.45 * min_cell))
    half_t = 0.5 * t
    outer_t = t  # outer shell thickness equals wall thickness
    fudge = max(tol * 5.0, 1e-6)

    opening_ratio = max(0.0, min(1.0, float(opening_ratio)))
    opening_height_ratio = max(0.0, min(1.0, float(opening_height_ratio)))
    open_density = max(0.0, min(1.0, float(open_density)))
    random.seed(int(seed))

    # Build the outer mass
    box_global = Box(Plane.WorldXY, Interval(0.0, length), Interval(0.0, depth), Interval(0.0, height))
    mass_brep = box_global.ToBrep()
    if mass_brep is None:
        return []

    # Precompute grid partition coordinates
    xs = [i * cx for i in range(nx + 1)]
    ys = [j * cy for j in range(ny + 1)]
    zs = [k * cz for k in range(nz + 1)]

    # Helper functions for patterns
    def open_x(i, j, k):
        # Opening on partition wall between cell (i,j,k) and (i+1,j,k), i in [0..nx-2]
        if pattern == 'checker':
            return ((i + j + k) % 2) == 0
        elif pattern == 'random':
            return random.random() < open_density
        elif pattern == 'grid':
            return (i % 2) == 0
        elif pattern == 'cross':
            return (j == ny // 2)  # open a corridor across Y center
        elif pattern == 'ring':
            return (j == 0 or j == ny - 1)
        else:
            return True

    def open_y(i, j, k):
        # Opening on partition wall between cell (i,j,k) and (i,j+1,k), j in [0..ny-2]
        if pattern == 'checker':
            return ((i + j + k) % 2) == 1
        elif pattern == 'random':
            return random.random() < open_density
        elif pattern == 'grid':
            return (j % 2) == 0
        elif pattern == 'cross':
            return (i == nx // 2)  # open a corridor across X center
        elif pattern == 'ring':
            return (i == 0 or i == nx - 1)
        else:
            return True

    def open_z(i, j, k):
        # Opening on partition floor/ceiling between cell (i,j,k) and (i,j,k+1), k in [0..nz-2]
        if not add_vertical_openings:
            return False
        if pattern == 'checker':
            return ((i + j + k) % 2) == 0
        elif pattern == 'random':
            return random.random() < open_density
        elif pattern == 'grid':
            return (k % 2) == 0
        elif pattern == 'cross':
            return (i == nx // 2 or j == ny // 2)
        elif pattern == 'ring':
            return (i in (0, nx - 1) or j in (0, ny - 1))
        else:
            return False

    def open_boundary(axis, side, i, j, k):
        # Openings on outer perimeter faces
        if pattern == 'checker':
            return ((i + j + k) % 2) == (0 if axis in ('x', 'z') else 1)
        elif pattern == 'random':
            return random.random() < open_density
        elif pattern == 'grid':
            return True
        elif pattern == 'cross':
            if axis == 'x':
                return j == ny // 2
            if axis == 'y':
                return i == nx // 2
            if axis == 'z':
                return (i == nx // 2 or j == ny // 2)
            return False
        elif pattern == 'ring':
            return True
        else:
            return True

    # Create internal voids for each cell (offset by t/2 on shared partitions, t on outer shell)
    voids = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                xmin, xmax = xs[i], xs[i + 1]
                ymin, ymax = ys[j], ys[j + 1]
                zmin, zmax = zs[k], zs[k + 1]
                ox0 = outer_t if i == 0 else half_t
                ox1 = outer_t if i == nx - 1 else half_t
                oy0 = outer_t if j == 0 else half_t
                oy1 = outer_t if j == ny - 1 else half_t
                oz0 = outer_t if k == 0 else half_t
                oz1 = outer_t if k == nz - 1 else half_t

                ix0 = xmin + ox0
                ix1 = xmax - ox1
                iy0 = ymin + oy0
                iy1 = ymax - oy1
                iz0 = zmin + oz0
                iz1 = zmax - oz1

                if ix1 - ix0 <= tol or iy1 - iy0 <= tol or iz1 - iz0 <= tol:
                    continue  # skip degenerate
                b = Box(Plane.WorldXY, Interval(ix0, ix1), Interval(iy0, iy1), Interval(iz0, iz1))
                vb = b.ToBrep()
                if vb: voids.append(vb)

    if not voids:
        return [mass_brep]

    # Subtract voids from mass
    try:
        solids = Brep.CreateBooleanDifference([mass_brep], voids, tol)
    except:
        solids = None
    if not solids:
        return [mass_brep]  # fallback

    # Opening sizes (interior)
    open_w_y = max(tol, opening_ratio * max(0.0, cy - t))
    open_h_z = max(tol, opening_height_ratio * max(0.0, cz - t))
    open_w_x = max(tol, opening_ratio * max(0.0, cx - t))  # for Y partitions
    open_h_z_z = max(tol, opening_ratio * max(0.0, cx - t))  # not used; kept for symmetry

    openings = []

    # Interior X partitions (between i and i+1)
    for i in range(nx - 1):
        x_plane = xs[i + 1]
        for j in range(ny):
            for k in range(nz):
                if not open_x(i, j, k):
                    continue
                y_center = ys[j] + 0.5 * cy
                z_center = zs[k] + 0.5 * cz
                x0 = x_plane - (t * 0.5 + fudge)
                x1 = x_plane + (t * 0.5 + fudge)
                y0 = max(0.0, y_center - 0.5 * open_w_y)
                y1 = min(depth, y_center + 0.5 * open_w_y)
                z0 = max(0.0, z_center - 0.5 * open_h_z)
                z1 = min(height, z_center + 0.5 * open_h_z)
                if y1 - y0 <= tol or z1 - z0 <= tol:
                    continue
                b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                ob = b.ToBrep()
                if ob: openings.append(ob)

    # Interior Y partitions (between j and j+1)
    for j in range(ny - 1):
        y_plane = ys[j + 1]
        for i in range(nx):
            for k in range(nz):
                if not open_y(i, j, k):
                    continue
                x_center = xs[i] + 0.5 * cx
                z_center = zs[k] + 0.5 * cz
                y0 = y_plane - (t * 0.5 + fudge)
                y1 = y_plane + (t * 0.5 + fudge)
                x0 = max(0.0, x_center - 0.5 * open_w_x)
                x1 = min(length, x_center + 0.5 * open_w_x)
                z0 = max(0.0, z_center - 0.5 * open_h_z)
                z1 = min(height, z_center + 0.5 * open_h_z)
                if x1 - x0 <= tol or z1 - z0 <= tol:
                    continue
                b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                ob = b.ToBrep()
                if ob: openings.append(ob)

    # Interior Z partitions (between k and k+1), optional
    if add_vertical_openings and nz > 1:
        open_w_xy = max(tol, opening_ratio * max(0.0, min(cx, cy) - t))
        open_t_z = t * 0.5 + fudge
        for k in range(nz - 1):
            z_plane = zs[k + 1]
            for i in range(nx):
                for j in range(ny):
                    if not open_z(i, j, k):
                        continue
                    x_center = xs[i] + 0.5 * cx
                    y_center = ys[j] + 0.5 * cy
                    x0 = max(0.0, x_center - 0.5 * open_w_xy)
                    x1 = min(length, x_center + 0.5 * open_w_xy)
                    y0 = max(0.0, y_center - 0.5 * open_w_xy)
                    y1 = min(depth, y_center + 0.5 * open_w_xy)
                    z0 = z_plane - open_t_z
                    z1 = z_plane + open_t_z
                    if x1 - x0 <= tol or y1 - y0 <= tol:
                        continue
                    b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                    ob = b.ToBrep()
                    if ob: openings.append(ob)

    # Boundary openings on outer shell (optional via pattern logic)
    # X- face (i==0) and X+ face (i==nx-1)
    for j in range(ny):
        for k in range(nz):
            # X- boundary
            if open_boundary('x', '-', 0, j, k):
                x0 = -fudge
                x1 = outer_t + fudge
                y_center = ys[j] + 0.5 * cy
                z_center = zs[k] + 0.5 * cz
                y0 = max(0.0, y_center - 0.5 * open_w_y)
                y1 = min(depth, y_center + 0.5 * open_w_y)
                z0 = max(0.0, z_center - 0.5 * open_h_z)
                z1 = min(height, z_center + 0.5 * open_h_z)
                if y1 - y0 > tol and z1 - z0 > tol:
                    b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                    ob = b.ToBrep()
                    if ob: openings.append(ob)
            # X+ boundary
            if open_boundary('x', '+', nx - 1, j, k):
                x0 = length - outer_t - fudge
                x1 = length + fudge
                y_center = ys[j] + 0.5 * cy
                z_center = zs[k] + 0.5 * cz
                y0 = max(0.0, y_center - 0.5 * open_w_y)
                y1 = min(depth, y_center + 0.5 * open_w_y)
                z0 = max(0.0, z_center - 0.5 * open_h_z)
                z1 = min(height, z_center + 0.5 * open_h_z)
                if y1 - y0 > tol and z1 - z0 > tol:
                    b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                    ob = b.ToBrep()
                    if ob: openings.append(ob)

    # Y- and Y+ boundaries
    for i in range(nx):
        for k in range(nz):
            # Y- boundary
            if open_boundary('y', '-', i, 0, k):
                y0 = -fudge
                y1 = outer_t + fudge
                x_center = xs[i] + 0.5 * cx
                z_center = zs[k] + 0.5 * cz
                x0 = max(0.0, x_center - 0.5 * open_w_x)
                x1 = min(length, x_center + 0.5 * open_w_x)
                z0 = max(0.0, z_center - 0.5 * open_h_z)
                z1 = min(height, z_center + 0.5 * open_h_z)
                if x1 - x0 > tol and z1 - z0 > tol:
                    b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                    ob = b.ToBrep()
                    if ob: openings.append(ob)
            # Y+ boundary
            if open_boundary('y', '+', i, ny - 1, k):
                y0 = depth - outer_t - fudge
                y1 = depth + fudge
                x_center = xs[i] + 0.5 * cx
                z_center = zs[k] + 0.5 * cz
                x0 = max(0.0, x_center - 0.5 * open_w_x)
                x1 = min(length, x_center + 0.5 * open_w_x)
                z0 = max(0.0, z_center - 0.5 * open_h_z)
                z1 = min(height, z_center + 0.5 * open_h_z)
                if x1 - x0 > tol and z1 - z0 > tol:
                    b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                    ob = b.ToBrep()
                    if ob: openings.append(ob)

    # Optionally boundary openings on Z faces (top/bottom) - typically not door-like, so skip unless vertical openings requested
    if add_vertical_openings:
        for i in range(nx):
            for j in range(ny):
                # Z- boundary
                if open_boundary('z', '-', i, j, 0):
                    z0 = -fudge
                    z1 = outer_t + fudge
                    x_center = xs[i] + 0.5 * cx
                    y_center = ys[j] + 0.5 * cy
                    span = max(tol, opening_ratio * max(0.0, min(cx, cy) - t))
                    x0 = max(0.0, x_center - 0.5 * span)
                    x1 = min(length, x_center + 0.5 * span)
                    y0 = max(0.0, y_center - 0.5 * span)
                    y1 = min(depth, y_center + 0.5 * span)
                    if x1 - x0 > tol and y1 - y0 > tol:
                        b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                        ob = b.ToBrep()
                        if ob: openings.append(ob)
                # Z+ boundary
                if open_boundary('z', '+', i, j, nz - 1):
                    z0 = height - outer_t - fudge
                    z1 = height + fudge
                    x_center = xs[i] + 0.5 * cx
                    y_center = ys[j] + 0.5 * cy
                    span = max(tol, opening_ratio * max(0.0, min(cx, cy) - t))
                    x0 = max(0.0, x_center - 0.5 * span)
                    x1 = min(length, x_center + 0.5 * span)
                    y0 = max(0.0, y_center - 0.5 * span)
                    y1 = min(depth, y_center + 0.5 * span)
                    if x1 - x0 > tol and y1 - y0 > tol:
                        b = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
                        ob = b.ToBrep()
                        if ob: openings.append(ob)

    # Apply opening subtractions
    result = list(solids)
    if openings:
        try:
            result = Brep.CreateBooleanDifference(solids, openings, tol)
        except:
            pass

    # Ensure we return Breps (even if boolean difference failed)
    if not result:
        result = list(solids)

    return list(result)"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = create_cubicle_structure(length=20.0, depth=12.0, height=9.0, nx=5, ny=3, nz=2, wall_thickness=0.25, opening_ratio=0.7, opening_height_ratio=0.8, pattern='cross', add_vertical_openings=True, seed=123)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = create_cubicle_structure(length=24.0, depth=18.0, height=9.0, nx=4, ny=6, nz=3, wall_thickness=0.18, opening_ratio=0.65, opening_height_ratio=0.7, pattern='random', open_density=0.35, add_vertical_openings=True, seed=99)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = create_cubicle_structure(length=30.0, depth=24.0, height=10.0, nx=6, ny=4, nz=2, wall_thickness=0.22, opening_ratio=0.55, opening_height_ratio=0.7, pattern='ring', open_density=0.2, add_vertical_openings=False, seed=7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
