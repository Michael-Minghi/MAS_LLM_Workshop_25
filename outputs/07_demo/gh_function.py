""" Summary:
The script defines a function that places isosceles triangular prism profiles along an X-linear sequence whose Y offset follows a sinusoid. For each index it computes X position, sinusoidal Y, and the curve tangent to derive local axes. It constructs a triangular polyline (base across a local X axis and apex in Z) and extrudes it along the local tangent by prism_length, optionally centering on the path. Each extrusion is converted to a Brep and capped to form solids when requested. The script samples three parameter sets, collects resulting Breps into a Grasshopper DataTree, enabling rapid facade massing variations. Iteratively."""

#! python 3
function_code = """def generate_sinusoidal_tri_prisms(n=20, base_width=6.0, prism_length=12.0, height=8.0, gap=2.0, amplitude=10.0, wavelength=40.0, phase=0.0, start_x=0.0, base_elevation=0.0, cap=True, center_on_path=True):
    \"""
    Create a set of triangular prisms arranged along a sinusoidal path, emulating a potential building massing.
    Returns a list of valid Breps (closed if cap=True).
    \"""
    import math
    import Rhino
    import Rhino.Geometry as rg

    breps = []
    if n < 1:
        return breps
    if base_width <= 0 or prism_length <= 0 or height <= 0 or wavelength <= 0:
        return breps

    tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance if Rhino.RhinoDoc.ActiveDoc else 1e-5

    pitch = float(base_width + gap)
    two_pi = 2.0 * math.pi

    Z = rg.Vector3d(0.0, 0.0, 1.0)

    for i in range(n):
        # Position along X and sinusoidal offset in Y
        x = start_x + i * pitch
        arg = two_pi * (x / wavelength) + phase
        y = amplitude * math.sin(arg)

        # Tangent of the sinusoid in XY: T = (1, dy/dx, 0)
        dydx = (two_pi / wavelength) * amplitude * math.cos(arg)
        T = rg.Vector3d(1.0, dydx, 0.0)
        if not T.Unitize():
            T = rg.Vector3d(1.0, 0.0, 0.0)

        # Local axes: X_local perpendicular to T in XY; Y_local along tangent; Z global up
        X_local = rg.Vector3d.CrossProduct(Z, T)
        if not X_local.Unitize():
            X_local = rg.Vector3d(1.0, 0.0, 0.0)
        Y_local = T

        # Center point on path
        origin = rg.Point3d(x, y, base_elevation)

        # Extrusion vector and optional centering of the prism about the path point
        extr_vec = rg.Vector3d(Y_local)
        extr_vec *= prism_length
        profile_origin = rg.Point3d(origin)
        if center_on_path:
            profile_origin -= rg.Vector3d(extr_vec) * 0.5

        # Build triangular profile (isosceles) in plane spanned by X_local and Z (normal is Y_local)
        half_w = 0.5 * base_width
        pL = profile_origin + (X_local * -half_w)
        pR = profile_origin + (X_local * half_w)
        pA = rg.Point3d(profile_origin)
        pA += Z * height

        poly = rg.Polyline([pL, pR, pA, pL])
        crv = rg.PolylineCurve(poly)

        if not crv.IsClosed or not crv.IsPlanar(tol):
            continue

        # Create extrusion using Surface.CreateExtrusion and cap planar holes for robust solids
        srf = rg.Surface.CreateExtrusion(crv, extr_vec)
        if not srf:
            continue
        brep = srf.ToBrep()
        if not brep:
            continue

        if cap:
            capped = brep.CapPlanarHoles(tol)
            if capped and capped.IsValid and capped.IsSolid:
                breps.append(capped)
        else:
            if brep.IsValid:
                breps.append(brep)

    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_sinusoidal_tri_prisms(n=30, base_width=4.0, prism_length=15.0, height=10.0, gap=1.5, amplitude=12.0, wavelength=50.0, phase=0.25, start_x=-25.0, base_elevation=0.0, cap=True, center_on_path=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_sinusoidal_tri_prisms(n=15, base_width=8.0, prism_length=20.0, height=6.0, gap=3.0, amplitude=20.0, wavelength=60.0, phase=1.0, start_x=10.0, base_elevation=2.0, cap=False, center_on_path=False)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_sinusoidal_tri_prisms(n=24, base_width=5.5, prism_length=18.0, height=9.0, gap=0.8, amplitude=15.0, wavelength=45.0, phase=0.75, start_x=-20.0, base_elevation=3.0, cap=True, center_on_path=False)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
