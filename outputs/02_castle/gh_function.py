""" Summary:
The script procedurally builds a vertical “princess” castle by stacking cube modules to form a tapered central tower and concentric ring towers. Parameters control levels, module_height, base_size, taper, and counts (merlons, ring_towers, etc.). Each central and ring level uses make_box_xy to create box Breps; sizes taper with height. Spherical Breps cap towers and—optionally—subtract from central cubes to create round windows using a robust boolean difference. Battlement merlons are arranged radially around the top. Geometry is validated and collected (safe_add) into a list, then converted to a Grasshopper data tree for Rhino/Grasshopper export for consistent results."""

#! python 3
function_code = """def generate_princess_castle_cubes_spheres(
    tower_levels=8,
    module_height=2.5,
    base_size=8.0,
    taper=0.35,
    ring_tower_count=4,
    ring_radius=12.0,
    ring_tower_levels=5,
    ring_tower_scale=0.55,
    merlon_count=16,
    merlon_size=1.2,
    merlon_height=1.2,
    sphere_cap_scale=0.6,
    mini_sphere_cap_scale=0.5,
    make_windows=True,
    window_radius=0.6,
    seed=1
):
    import math
    import random
    import Rhino
    import Rhino.Geometry as rg

    random.seed(seed)
    tol = 1e-3
    try:
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is not None and hasattr(doc, "ModelAbsoluteTolerance"):
            tol = max(1e-6, float(doc.ModelAbsoluteTolerance))
    except:
        pass

    geos = []

    # Helpers
    def clamp(v, a, b):
        return max(a, min(b, v))

    def safe_add(brep):
        if brep is not None:
            try:
                if hasattr(brep, "IsValid"):
                    if brep.IsValid:
                        geos.append(brep)
                else:
                    geos.append(brep)
            except:
                pass

    def make_box_xy(xmin, xmax, ymin, ymax, zmin, zmax):
        # Ensure min < max
        if xmin > xmax: xmin, xmax = xmax, xmin
        if ymin > ymax: ymin, ymax = ymax, ymin
        if zmin > zmax: zmin, zmax = zmax, zmin
        if abs(xmax - xmin) < tol or abs(ymax - ymin) < tol or abs(zmax - zmin) < tol:
            return None
        box = rg.Box(rg.Plane.WorldXY, rg.Interval(xmin, xmax), rg.Interval(ymin, ymax), rg.Interval(zmin, zmax))
        brep = box.ToBrep()
        if brep is None or not brep.IsValid:
            return None
        return brep

    def central_size_at_level(i, levels, base, taper_factor):
        if levels <= 1:
            t = 0.0
        else:
            t = float(i) / float(levels - 1)
        s = base * (1.0 - taper_factor * t)
        # Keep a reasonable minimum so the top doesn't disappear
        return max(s, base * 0.35)

    def ring_size_at_level(j, levels, base, scale):
        if levels <= 1:
            t = 0.0
        else:
            t = float(j) / float(levels - 1)
        # Gentle taper on mini-towers
        s0 = base * scale
        s = s0 * (1.0 - 0.25 * t)
        return max(s, s0 * 0.5)

    def boolean_diff_safe(base_brep, cutters, tol_val):
        # Robust boolean difference that never throws and preserves base if it fails
        if base_brep is None:
            return None
        try:
            if not isinstance(cutters, (list, tuple)):
                cutters = [cutters] if cutters is not None else []
            cutters = [c for c in cutters if c is not None and getattr(c, "IsValid", False)]
            if len(cutters) == 0:
                return base_brep
            res = rg.Brep.CreateBooleanDifference([base_brep], cutters, tol_val)
            if res and len(res) > 0:
                # pick the largest result if multiple
                try:
                    vols = []
                    for b in res:
                        if b is None or not b.IsValid:
                            vols.append(-1.0)
                        else:
                            mp = rg.VolumeMassProperties.Compute(b)
                            vols.append(mp.Volume if mp is not None else -1.0)
                    idx = max(range(len(res)), key=lambda k: vols[k])
                    out = res[idx]
                    if out is not None and out.IsValid:
                        return out
                except:
                    if res[0] is not None and res[0].IsValid:
                        return res[0]
        except:
            pass
        return base_brep

    # Determine which central levels get windows (avoid base/top)
    if tower_levels >= 4:
        wl1 = clamp(int(round(tower_levels * 0.33)), 1, tower_levels - 2)
        wl2 = clamp(int(round(tower_levels * 0.66)), 1, tower_levels - 2)
        window_levels = sorted(set([wl1, wl2]))
    else:
        window_levels = [max(0, tower_levels // 2)]

    # Build central tower (stacked cubes with optional spherical window subtractions)
    for i in range(max(0, tower_levels)):
        z0 = i * module_height
        z1 = z0 + module_height
        size_i = central_size_at_level(i, tower_levels, base_size, taper)
        half = 0.5 * size_i
        tower_brep = make_box_xy(-half, half, -half, half, z0, z1)

        # Spherical windows on selected levels (robust, no null refs)
        if tower_brep is not None and make_windows and (i in window_levels) and window_radius > tol:
            dirs = [(1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)]
            cutters = []
            for dx, dy in dirs:
                px = dx * (half - window_radius * 0.25)
                py = dy * (half - window_radius * 0.25)
                pz = z0 + 0.5 * module_height
                sph = rg.Sphere(rg.Point3d(px, py, pz), window_radius)
                s_brep = sph.ToBrep()
                if s_brep is not None and s_brep.IsValid:
                    cutters.append(s_brep)
            if cutters:
                tower_brep = boolean_diff_safe(tower_brep, cutters, tol)

        safe_add(tower_brep)

    # Central sphere cap
    top_size = central_size_at_level(max(0, tower_levels - 1), max(1, tower_levels), base_size, taper)
    cap_r = 0.5 * top_size * sphere_cap_scale
    if cap_r > tol:
        cap_center = rg.Point3d(0.0, 0.0, max(0, tower_levels) * module_height + cap_r)
        cap_brep = rg.Sphere(cap_center, cap_r).ToBrep()
        safe_add(cap_brep)

    # Battlements (merlon cubes) around central tower rim
    if merlon_count > 0 and merlon_size > tol and merlon_height > tol:
        z_merlon0 = max(0, tower_levels) * module_height
        z_merlon1 = z_merlon0 + merlon_height
        r_merlon = 0.5 * top_size + merlon_size * 0.6
        for k in range(merlon_count):
            ang = 2.0 * math.pi * float(k) / float(merlon_count)
            cx = r_merlon * math.cos(ang)
            cy = r_merlon * math.sin(ang)
            h = 0.5 * merlon_size
            safe_add(make_box_xy(cx - h, cx + h, cy - h, cy + h, z_merlon0, z_merlon1))

    # Ring of mini-towers with sphere caps
    if ring_tower_count > 0 and ring_radius > tol and ring_tower_levels > 0:
        for ti in range(ring_tower_count):
            ang = 2.0 * math.pi * float(ti) / float(ring_tower_count)
            cx = ring_radius * math.cos(ang)
            cy = ring_radius * math.sin(ang)
            # Stack cubes for this mini-tower
            for j in range(ring_tower_levels):
                z0 = j * module_height
                z1 = z0 + module_height
                size_j = ring_size_at_level(j, ring_tower_levels, base_size, ring_tower_scale)
                h = 0.5 * size_j
                safe_add(make_box_xy(cx - h, cx + h, cy - h, cy + h, z0, z1))

            # Cap sphere for mini-tower
            top_size_j = ring_size_at_level(max(0, ring_tower_levels - 1), max(1, ring_tower_levels), base_size, ring_tower_scale)
            cap_rj = 0.5 * top_size_j * mini_sphere_cap_scale
            if cap_rj > tol:
                cap_cj = rg.Point3d(cx, cy, ring_tower_levels * module_height + cap_rj)
                safe_add(rg.Sphere(cap_cj, cap_rj).ToBrep())

    return geos"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_princess_castle_cubes_spheres(tower_levels=10, module_height=2.8, base_size=10.0, taper=0.3, ring_tower_count=6, ring_radius=15.0, ring_tower_levels=4, ring_tower_scale=0.6, merlon_count=20, merlon_size=1.4, merlon_height=1.5, sphere_cap_scale=0.75, mini_sphere_cap_scale=0.5, make_windows=True, window_radius=0.7, seed=42)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_princess_castle_cubes_spheres(tower_levels=6, module_height=3.0, base_size=12.0, taper=0.25, ring_tower_count=8, ring_radius=18.0, ring_tower_levels=3, ring_tower_scale=0.5, merlon_count=12, merlon_size=1.0, merlon_height=1.2, sphere_cap_scale=0.8, mini_sphere_cap_scale=0.6, make_windows=False, window_radius=0.5, seed=7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_princess_castle_cubes_spheres(tower_levels=9, module_height=2.2, base_size=9.0, taper=0.4, ring_tower_count=5, ring_radius=14.0, ring_tower_levels=6, ring_tower_scale=0.5, merlon_count=18, merlon_size=1.0, merlon_height=1.0, sphere_cap_scale=0.65, mini_sphere_cap_scale=0.55, make_windows=True, window_radius=0.8, seed=123)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
