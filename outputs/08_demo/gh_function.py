""" Summary:
The script builds an equilateral triangular lattice in XY using a module parameter, creating grid points via lattice vectors. For each triangular cell it computes the centroid and samples a sinusoidal height field (X and Y waves with wavelengths, phases, and combine modes like sum, product, X or Y). Heights are clamped and offset by a base_height to avoid degeneracy. Each planar triangle is extruded along +Z by the sampled height to form a triangular prism; side faces are lofted and planar holes capped to produce closed Breps. The function returns a list of triangular-prism elements for iterative facade exploration."""

#! python 3
function_code = """def generate_sinusoidal_triangular_prisms(rows=10, cols=16, module=4.0, base_height=2.5, amplitude=6.0, wavelength_x=None, wavelength_y=None, phase_x=0.0, phase_y=0.0, combine_mode="sum", origin=None, clamp_min=0.2, clamp_max=None):
    \"""
    Create a massing made of triangular prisms laid on an equilateral triangular grid,
    with heights modulated by a sinusoidal field along the global X and Y axes.
    The Z axis is treated as the vertical (height) direction.

    Outputs:
    - list of Rhino.Geometry.Brep: Closed Breps of triangular prisms arranged in a sinusoidal pattern.
    \"""
    import math
    import Rhino
    import Rhino.Geometry as rg

    # Model tolerance
    tol = 1e-6
    doc = Rhino.RhinoDoc.ActiveDoc
    if doc:
        try:
            tol = max(1e-7, float(doc.ModelAbsoluteTolerance))
        except:
            pass

    # Basic validation and defaults
    rows = max(1, int(rows))
    cols = max(1, int(cols))
    module = float(module)
    if module <= 0:
        raise ValueError("Parameter 'module' must be > 0.")
    base_height = float(base_height)
    amplitude = float(amplitude)
    clamp_min = max(0.0, float(clamp_min))
    if clamp_max is not None:
        clamp_max = max(clamp_min, float(clamp_max))

    # Grid base origin
    if origin is None:
        origin = rg.Point3d(0.0, 0.0, 0.0)

    # Equilateral triangle geometry in XY
    a = module
    h = (math.sqrt(3.0) / 2.0) * a
    # Lattice vectors for equilateral triangular grid (planar in XY)
    u = rg.Vector3d(a, 0.0, 0.0)
    v = rg.Vector3d(a * 0.5, h, 0.0)

    # Wavelength defaults if not provided
    if wavelength_x is None or wavelength_x == 0:
        wavelength_x = cols * a
    if wavelength_y is None or wavelength_y == 0:
        wavelength_y = rows * h

    # Wave numbers (guard against zero to avoid division by zero)
    kx = (2.0 * math.pi / float(wavelength_x)) if abs(float(wavelength_x)) > 1e-12 else 0.0
    ky = (2.0 * math.pi / float(wavelength_y)) if abs(float(wavelength_y)) > 1e-12 else 0.0

    # Helper to get grid point
    def grid_point(i, j):
        return rg.Point3d(
            origin.X + i * u.X + j * v.X,
            origin.Y + i * u.Y + j * v.Y,
            origin.Z
        )

    # Prepare grid points (size (cols+1) x (rows+1))
    pts = [[grid_point(i, j) for j in range(rows + 1)] for i in range(cols + 1)]

    # Wave combiner
    cm = (combine_mode or "sum").lower()
    def wave_value(x, y):
        sx = math.sin(kx * x + float(phase_x)) if kx != 0.0 else 0.0
        sy = math.sin(ky * y + float(phase_y)) if ky != 0.0 else 0.0
        if cm == "product":
            return sx * sy
        elif cm == "x":
            return sx
        elif cm == "y":
            return sy
        else:
            return 0.5 * (sx + sy)

    breps = []

    # Iterate cells and make two equilateral triangles per cell
    for i in range(cols):
        for j in range(rows):
            # Triangle 1: P(i,j), P(i+1,j), P(i,j+1)
            t1 = (pts[i][j], pts[i + 1][j], pts[i][j + 1])
            # Triangle 2: P(i+1,j+1), P(i+1,j), P(i,j+1)
            t2 = (pts[i + 1][j + 1], pts[i + 1][j], pts[i][j + 1])

            for tri in (t1, t2):
                A, B, C = tri
                # Centroid for sampling height field
                cx = (A.X + B.X + C.X) / 3.0
                cy = (A.Y + B.Y + C.Y) / 3.0

                f = wave_value(cx, cy)
                H = base_height + amplitude * f
                # Clamp height to ensure non-degenerate prisms
                if H < clamp_min:
                    H = clamp_min
                if clamp_max is not None and H > clamp_max:
                    H = clamp_max

                if H <= tol:
                    continue

                # Build the planar triangle curve
                pl = rg.Polyline([A, B, C, A])
                crv = rg.PolylineCurve(pl)
                if not crv.IsClosed or not crv.IsValid:
                    continue

                # Create top curve by translation along +Z
                ext_vec = rg.Vector3d(0.0, 0.0, H)
                top_crv = crv.DuplicateCurve()
                xform = rg.Transform.Translation(ext_vec)
                if not top_crv.Transform(xform):
                    continue

                # Loft side surfaces and cap planar holes to ensure solid, valid breps
                lofts = rg.Brep.CreateFromLoft([crv, top_crv], rg.Point3d.Unset, rg.Point3d.Unset, rg.LoftType.Straight, False)
                if not lofts or len(lofts) == 0:
                    continue
                side_brep = lofts[0]
                solid = side_brep.CapPlanarHoles(tol)
                if solid is not None and solid.IsValid and solid.IsSolid:
                    # Merge coplanar faces to clean up any tiny artifacts
                    try:
                        solid.MergeCoplanarFaces(tol)
                    except:
                        pass
                    if solid.IsValid and solid.IsSolid:
                        breps.append(solid)

    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_sinusoidal_triangular_prisms(rows=12, cols=20, module=2.5, base_height=3.0, amplitude=5.0, wavelength_x=50.0, wavelength_y=30.0, phase_x=0.0, phase_y=1.57, combine_mode="product", origin=None, clamp_min=0.5, clamp_max=10.0)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_sinusoidal_triangular_prisms(rows=8, cols=12, module=3.0, base_height=1.5, amplitude=4.0, wavelength_x=36.0, wavelength_y=24.0, phase_x=0.5, phase_y=1.0, combine_mode="y", origin=None, clamp_min=0.2, clamp_max=6.0)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_sinusoidal_triangular_prisms(rows=15, cols=10, module=2.0, base_height=0.5, amplitude=8.0, wavelength_x=20.0, wavelength_y=40.0, phase_x=0.25, phase_y=0.75, combine_mode="x", origin=None, clamp_min=0.3, clamp_max=12.0)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
