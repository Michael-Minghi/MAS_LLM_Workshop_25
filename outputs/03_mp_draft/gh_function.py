""" Summary:
The script builds a dangerous vertical facade by stacking rotated cubes along a helical path. Each level places a cube at an offset radius and rotated by a twist angle, forming a precarious spiral tower. Around each cube it places spheres: some subtracted from the cube as carved voids, others added as protruding hazards. Randomized directional offsets and vertical jitter (controlled by a seed) vary sphere positions. Parameters (levels, cube_size, twist_per_level, helix_radius, sphere_radius, spheres_per_level, hazard_ratio) tune scale and aggression. Boolean difference produces voided cubes; the function returns Rhino Breps for visualization and fabrication. It matches the reference image's cube-sphere grammar."""

#! python 3
function_code = """def generate_dangerous_vertical_stack(total_height=30.0,
                                      levels=12,
                                      cube_size=3.0,
                                      twist_per_level_deg=22.5,
                                      helix_radius=1.0,
                                      sphere_radius=1.2,
                                      spheres_per_level=3,
                                      hazard_ratio=0.6,
                                      seed=42,
                                      carve_voids=True):
    \"""
    Generate a dangerous vertical architectural structure using only cubes and spheres.

    The function builds a vertical, helical stack of rotated cubes (solids) to form
    a precarious tower. Around each cube, spherical geometries are placed to either:
      - carve voids (subtractive spheres) inside the cubes, and/or
      - protrude outward (additive spheres) to increase "danger".
    Only cubes and spheres are created; voids are produced via boolean subtraction.

    Inputs:
      - total_height (float, meters): Overall vertical extent of the structure.
      - levels (int): Number of stacked cubes along the vertical axis.
      - cube_size (float, meters): Edge length of each cube.
      - twist_per_level_deg (float, degrees): Rotation applied to each successive cube.
      - helix_radius (float, meters): Radial offset of cube centers from the Z-axis, forming a helical stack.
      - sphere_radius (float, meters): Radius of all spheres used for voids/protrusions.
      - spheres_per_level (int): Total spheres per cube (sum of void-carving and protruding spheres).
      - hazard_ratio (float, 0..1): Fraction of spheres per level used as outward protrusions (hazards).
                                     The remainder are used as void carvers (subtractive).
      - seed (int): Random seed for reproducible placement of spheres.
      - carve_voids (bool): If True, subtract void spheres from cubes. If False, all spheres are additive only.

    Output:
      - list of Rhino.Geometry.Brep: A list of closed Breps containing the resulting cubes (with carved voids if enabled)
                                     and the additional protruding spheres as separate solids. All units are meters.
    \"""
    import math
    import random
    import Rhino

    rg = Rhino.Geometry
    doc = Rhino.RhinoDoc.ActiveDoc
    tol = doc.ModelAbsoluteTolerance if doc else 1e-3

    rnd = random.Random(seed)

    # Helper: compute largest brep by volume (fallback to bbox volume if needed)
    def _largest_brep(breps):
        if not breps:
            return None
        best = None
        best_val = -1.0
        for b in breps:
            vm = rg.VolumeMassProperties.Compute(b)
            if vm:
                val = vm.Volume
            else:
                bb = b.GetBoundingBox(True)
                if not bb.IsValid: 
                    continue
                d = bb.Diagonal
                val = abs(d.X * d.Y * d.Z)
            if val > best_val:
                best_val = val
                best = b
        return best

    # Helper: subtract a list of cutter breps from a target brep, return single best result or original on failure
    def _boolean_difference_single(target_brep, cutter_breps, tolerance):
        if not cutter_breps or not target_brep:
            return target_brep
        try:
            res = rg.Brep.CreateBooleanDifference([target_brep], cutter_breps, tolerance)
            if res and len(res) > 0:
                largest = _largest_brep(res)
                return largest if largest else target_brep
            else:
                return target_brep
        except Exception:
            return target_brep

    # Build directional vectors around a rotated local frame for consistent sphere placement
    def _direction_set(plane):
        dirs = []
        ax = plane.XAxis
        ay = plane.YAxis
        # Primary axes
        dirs.extend([ax, ay, -ax, -ay])
        # Diagonals
        d1 = rg.Vector3d(ax)
        d1 += ay; d1.Unitize()
        d2 = rg.Vector3d(ax)
        d2 -= ay; d2.Unitize()
        d3 = rg.Vector3d(-ax)
        d3 += ay; d3.Unitize()
        d4 = rg.Vector3d(-ax)
        d4 -= ay; d4.Unitize()
        dirs.extend([d1, d2, d3, d4])
        return dirs

    # Generate level heights
    zs = []
    if levels <= 1:
        zs = [0.0]
    else:
        step = float(total_height) / float(levels - 1)
        zs = [i * step for i in range(levels)]

    result_breps = []

    for i, z in enumerate(zs):
        # Helical center position
        ang = math.radians(twist_per_level_deg) * i
        cx = helix_radius * math.cos(ang)
        cy = helix_radius * math.sin(ang)
        cpt = rg.Point3d(cx, cy, z)

        # Create rotated local plane for the cube
        pl = rg.Plane.WorldXY
        pl.Origin = cpt
        rot = rg.Transform.Rotation(ang, rg.Vector3d.ZAxis, cpt)
        pl.Transform(rot)

        # Create the cube as a Brep via Box
        half = cube_size * 0.5
        bx = rg.Interval(-half, half)
        by = rg.Interval(-half, half)
        bz = rg.Interval(-half, half)
        box = rg.Box(pl, bx, by, bz)
        cube_brep = box.ToBrep()

        # Direction set for sphere placements
        dirs = _direction_set(pl)

        # Determine counts of hazard vs void spheres
        hazard_count = int(round(max(0, min(1, hazard_ratio)) * spheres_per_level))
        void_count = max(0, spheres_per_level - hazard_count)

        # Build void spheres (inside)
        void_cutters = []
        for _ in range(void_count):
            d = rnd.choice(dirs)
            # place inside the cube towards face, not reaching outside
            t = 0.35 + 0.1 * rnd.random()  # fraction of half distance
            offset_vec = rg.Vector3d(d)
            offset_vec *= (half * t)
            # small vertical jitter to make danger less predictable
            vz = rg.Vector3d(0, 0, (rnd.random() - 0.5) * half * 0.2)
            center = cpt + offset_vec + vz
            sph = rg.Sphere(center, sphere_radius)
            void_cutters.append(sph.ToBrep())

        # Carve voids if enabled
        if carve_voids and void_cutters:
            cube_brep = _boolean_difference_single(cube_brep, void_cutters, tol)

        # Build hazard spheres (outside)
        hazard_spheres = []
        for _ in range(hazard_count):
            d = rnd.choice(dirs)
            # place outside the cube beyond the face to protrude
            t = (half + sphere_radius * (0.7 + 0.3 * rnd.random()))
            offset_vec = rg.Vector3d(d)
            offset_vec *= t
            # small vertical jitter
            vz = rg.Vector3d(0, 0, (rnd.random() - 0.5) * half * 0.3)
            center = cpt + offset_vec + vz
            sph = rg.Sphere(center, sphere_radius)
            hazard_spheres.append(sph.ToBrep())

        # Append cube and hazard spheres as separate Breps
        if cube_brep:
            result_breps.append(cube_brep)
        if hazard_spheres:
            result_breps.extend(hazard_spheres)

    return result_breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_dangerous_vertical_stack(total_height=20.0, levels=10, cube_size=2.5, twist_per_level_deg=30.0, helix_radius=1.5, sphere_radius=0.8, spheres_per_level=6, hazard_ratio=0.5, seed=12345, carve_voids=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_dangerous_vertical_stack(total_height=45.0, levels=15, cube_size=2.2, twist_per_level_deg=18.0, helix_radius=1.8, sphere_radius=1.0, spheres_per_level=5, hazard_ratio=0.75, seed=2025, carve_voids=False)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_dangerous_vertical_stack(total_height=32.0, levels=9, cube_size=3.5, twist_per_level_deg=36.0, helix_radius=2.0, sphere_radius=1.1, spheres_per_level=7, hazard_ratio=0.65, seed=777, carve_voids=True)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
