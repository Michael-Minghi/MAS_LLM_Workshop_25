""" Summary:
This script tiles the XY plane with an equilateral-triangle lattice and extrudes each triangular cell upward to form vertical triangular prisms. For every grid cell it creates two triangles, computes each triangle’s centroid, and samples a sinusoidal height function (base_height + amplitude*sin(k*pos+phase)) using pos from x, y, or radial distance to a center. Heights are clamped by min_height. Triangles are converted to polyline curves and extruded along +Z into capped Breps (optional). Parameters control module size, columns/rows, amplitude, wavelength, phase, origin and center. The function returns a list/tree of Breps describing the sinusoidal prism massing useful for facade massing studies."""

#! python 3
function_code = """def generate_sinusoidal_triangular_prisms(module=5.0, cols=10, rows=6, base_height=6.0, amplitude=8.0, wavelength=30.0, axis='x', phase=0.0, origin=(0.0, 0.0, 0.0), center=(0.0, 0.0), min_height=0.25, cap=True):
    \"""
    Create a massing composed of vertical triangular prisms whose heights follow a sinusoidal pattern.

    The function tiles the XY-plane with equilateral triangular cells (two triangles per rectangular cell)
    and extrudes each triangle upward along +Z to form a prism. The height of each prism varies
    according to a sinusoidal function evaluated at the centroid of the triangle, producing a wave-like
    building massing. Dimensions are in meters; Z is the vertical axis.

    Outputs:
        list[Rhino.Geometry.Brep]: List of valid Breps representing the triangular prisms.
    \"""
    import math
    import Rhino.Geometry as rg

    # Validate and prepare parameters
    s = float(max(module, 1e-6))
    cols = max(int(cols), 1)
    rows = max(int(rows), 1)
    base_height = float(base_height)
    amplitude = float(amplitude)
    wavelength = float(wavelength)
    phase = float(phase)
    min_height = float(max(min_height, 0.0))
    cap = bool(cap)

    # Geometry constants for equilateral triangles
    h_row = s * math.sqrt(3.0) * 0.5  # vertical pitch between rows

    # Origin and center handling
    try:
        ox, oy = (origin.X, origin.Y) if hasattr(origin, "X") else (float(origin[0]), float(origin[1]))
    except:
        ox, oy = 0.0, 0.0

    cx, cy = float(center[0]), float(center[1])

    # Wavenumber (avoid division by zero)
    k = (2.0 * math.pi) / (wavelength if abs(wavelength) > 1e-9 else 1e-9)

    # Helper to compute height at a point
    ax = axis.lower() if isinstance(axis, str) else 'x'
    def prism_height(px, py):
        if ax.startswith('x'):
            pos = px
        elif ax.startswith('y'):
            pos = py
        elif ax.startswith('r'):
            pos = math.hypot(px - cx, py - cy)
        else:
            pos = px  # default to 'x' if axis is invalid
        h = base_height + amplitude * math.sin(k * pos + phase)
        return max(h, min_height)

    breps = []

    # Build triangular grid and extrude each triangle with sinusoidal height
    for r in range(rows):
        y0 = oy + r * h_row
        y1 = oy + (r + 1) * h_row
        shift0 = (r % 2) * (s * 0.5)
        shift1 = ((r + 1) % 2) * (s * 0.5)

        for c in range(cols):
            x0 = ox + c * s
            x1 = ox + (c + 1) * s

            # Define four lattice points that form two equilateral triangles
            P0 = rg.Point3d(x0 + shift0, y0, 0.0)
            P1 = rg.Point3d(x1 + shift0, y0, 0.0)
            P2a = rg.Point3d(x0 + shift1, y1, 0.0)
            P2b = rg.Point3d(x1 + shift1, y1, 0.0)

            # Triangle 1: P0, P1, P2a
            cx1 = (P0.X + P1.X + P2a.X) / 3.0
            cy1 = (P0.Y + P1.Y + P2a.Y) / 3.0
            h1 = prism_height(cx1, cy1)
            crv1 = rg.PolylineCurve([P0, P1, P2a, P0])
            ext1 = rg.Extrusion.Create(crv1, h1, cap)
            if ext1:
                brep1 = ext1.ToBrep(True)
                if brep1 and brep1.IsValid:
                    breps.append(brep1)

            # Triangle 2: P1, P2a, P2b
            cx2 = (P1.X + P2a.X + P2b.X) / 3.0
            cy2 = (P1.Y + P2a.Y + P2b.Y) / 3.0
            h2 = prism_height(cx2, cy2)
            crv2 = rg.PolylineCurve([P1, P2a, P2b, P1])
            ext2 = rg.Extrusion.Create(crv2, h2, cap)
            if ext2:
                brep2 = ext2.ToBrep(True)
                if brep2 and brep2.IsValid:
                    breps.append(brep2)

    return breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_sinusoidal_triangular_prisms(module=5.0, cols=24, rows=12, base_height=6.0, amplitude=8.0, wavelength=30.0, axis='r', phase=0.0, origin=(0.0, 0.0, 0.0), center=(60.0, 30.0), min_height=0.5, cap=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_sinusoidal_triangular_prisms(module=3.0, cols=15, rows=8, base_height=4.0, amplitude=6.0, wavelength=20.0, axis='y', phase=0.78539816339, origin=(10.0, -5.0, 0.0), center=(22.5, 12.0), min_height=0.1, cap=False)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_sinusoidal_triangular_prisms(module=4.5, cols=20, rows=10, base_height=5.5, amplitude=10.0, wavelength=25.0, axis='x', phase=1.57079632679, origin=(-15.0, 5.0, 0.0), center=(10.0, 15.0), min_height=0.2, cap=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
