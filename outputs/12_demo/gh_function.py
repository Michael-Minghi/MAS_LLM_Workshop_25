""" Summary:
Iterating level-by-level, the script assembles cubic modules into a three-part tower: Podium (L0–5) uses a doubled footprint with no twist; Shaft (L6–65) tapers 0.3%; Crown (L66–80) steps back one module on opposing X faces every two levels and adds +1° rotation. It computes cumulative 6-level band transforms—±3° rotations, alternating X/Y one-module shifts, and one-module perimeter setbacks on bands divisible by 3. A solid 3×3 core is preserved; NE/SW 2-module vertical slots carved L10–70; double-height sky-lobbies remove 50% of perimeter every 15 levels. Height-based porosity p(z)=0.10+0.30(z/H), clamped 0.40, randomly removes perimeter modules. Cubes are created, transformed, and returned as Breps."""

#! python 3
function_code = """def generate_tower_geometry(module_size=6.0, total_levels=81, base_modules=10, seed=1):
    \"""
    Generate a vertical tower composed of cubic modules (Breps) with a three-part massing (Podium, Shaft, Crown),
    governed by 6-level rhythmic band rules and structured porosity/voids.

    Concept translation:
    - Podium (L0–5): footprint = 2× base 10×10 module plan, 0° twist.
    - Shaft (L6–65): tapers 0.3%/level from base_modules toward smaller plans (capped at >=3×3), rotation from 6-level bands.
    - Crown (L66–80): steps back 1 module on two opposing faces (±X) every 2 levels; rotation increases +1°/level.
    - 6-level band rule (band b = floor(L/6)):
        - Rotate cumulatively: +3° if b is odd, −3° if b is even (bands accumulate).
        - Shift laterally 1 module per band, alternating +X, +Y (cumulative shift, bands accumulate starting from band 1).
        - Bands divisible by 3: apply a 1-module perimeter setback (reduces plan by 1 module each face, i.e., -2 in X and -2 in Y).
    - Porosity/voids tied to structure:
        - Keep a solid 3×3 core at all levels.
        - Carve two continuous vertical slots, 2 modules wide, at world NE and SW corners from L10–70.
        - Insert double-height sky-lobbies every 15 levels by removing 50% of perimeter modules on levels {15,16,30,31,45,46,60,61}.
        - Apply additional height-based porosity p(z) = clamp(0.10 + 0.30*(z/H), 0.40) to perimeter modules.

    Parameters:
    - module_size (float): Edge length of each cube in meters (also used for vertical module step).
    - total_levels (int): Number of levels (L0 to L(total_levels-1)). Default 81 -> L0–80.
    - base_modules (int): Base maximum plan dimension (modules per side) for the shaft reference; default 10.
    - seed (int): Random seed for reproducible porosity and sky-lobby selections.

    Returns:
    - list[Rhino.Geometry.Brep]: A list of Breps representing all remaining cubic modules.
    \"""
    import math
    import random
    import Rhino
    from Rhino.Geometry import Point3d, Plane, Interval, Box, Brep, Transform, Vector3d

    # Helper clamp
    def clamp(val, a, b):
        return max(a, min(b, val))

    # Precompute total height for porosity gradient
    H = float(total_levels) * module_size

    # Sky-lobby levels (double height: remove 50% perimeter on these levels)
    sky_levels = set()
    for base in (15, 30, 45, 60):
        if 0 <= base < total_levels:
            sky_levels.add(base)
        if 0 <= base + 1 < total_levels:
            sky_levels.add(base + 1)

    # Base shaft width (world) used to anchor vertical slots (fixed in world space)
    shaft_side_world = base_modules * module_size
    slot_w = 2.0 * module_size  # slot width as specified (2 modules wide)

    # Cumulative band transforms: define functions to compute shift and rotation up to current band
    def cumulative_shift_for_band(band_index):
        # Bands start at 0 (levels 0-5). We do not shift the podium band (0).
        s = Vector3d(0.0, 0.0, 0.0)
        for b in range(1, band_index + 1):
            if b % 2 == 1:  # odd band -> +Y
                s += Vector3d(0.0, module_size, 0.0)
            else:           # even band -> +X
                s += Vector3d(module_size, 0.0, 0.0)
        return s

    def cumulative_rotation_deg_for_band(band_index, is_podium):
        if is_podium:
            return 0.0
        ang = 0.0
        for b in range(1, band_index + 1):
            ang += 3.0 if (b % 2 == 1) else -3.0
        return ang

    # Utility to ensure odd counts and minimum 3 for 3x3 core
    def ensure_odd_min3(n):
        n = int(max(3, n))
        if n % 2 == 0:
            n += 1
        return n

    # RNG setup
    base_rng = random.Random(seed)

    # Output list
    out_breps = []

    for L in range(total_levels):
        # Determine band and flags
        band = L // 6
        is_podium = (L <= 5)
        is_shaft = (6 <= L <= 65)
        is_crown = (L >= 66)

        # Nominal plan (modules per side) before band setbacks and crown steps
        if is_podium:
            nx_nom = ny_nom = 2 * base_modules
        else:
            # Shaft taper 0.3% per level starting at L6
            # Use base_modules as max at L6, taper up the tower
            taper_levels = max(0, L - 6)
            scale = 1.0 - 0.003 * taper_levels
            n_nom = int(round(base_modules * scale))
            n_nom = max(3, min(base_modules, n_nom))
            nx_nom = ny_nom = n_nom

        # Apply band perimeter setback on bands divisible by 3 (not on podium to keep clarity)
        if (not is_podium) and (band % 3 == 0):
            nx_nom -= 2
            ny_nom -= 2

        # Crown step-back: reduce X-extent by 1 module on two opposing faces every 2 levels
        if is_crown:
            steps = ((L - 66) // 2) + 1  # 1 step for 66–67, 2 for 68–69, etc.
            nx_nom -= 2 * steps  # reduce both +X and -X faces by 1 per step

        # Enforce minimum and odd counts (to preserve centered 3x3 core)
        nx = ensure_odd_min3(nx_nom)
        ny = ensure_odd_min3(ny_nom)

        # Compute cumulative transforms for this level
        shift_vec = cumulative_shift_for_band(band)
        rot_deg = cumulative_rotation_deg_for_band(band, is_podium)
        if is_crown:
            # Crown increases rotation by +1°/level from L66 upwards
            rot_deg += float(L - 65)

        rot_rad = math.radians(rot_deg)
        T_rot = Transform.Rotation(rot_rad, Point3d(0.0, 0.0, 0.0))
        T_shift = Transform.Translation(shift_vec)
        T_level = T_rot
        T_level *= T_shift

        # Level geometry parameters
        bottom_z = L * module_size
        top_z = bottom_z + module_size

        # Porosity
        z_center = bottom_z + 0.5 * module_size
        p = clamp(0.10 + 0.30 * (z_center / H), 0.0, 0.40)

        # Index extents (odd counts, centered)
        hx = nx // 2
        hy = ny // 2

        # Precompute perimeter indices (excluding core)
        perimeter_indices = []
        all_indices = []
        for i in range(-hx, hx + 1):
            for j in range(-hy, hy + 1):
                all_indices.append((i, j))
                at_perimeter = (abs(i) == hx) or (abs(j) == hy)
                in_core = (abs(i) <= 1 and abs(j) <= 1)
                if at_perimeter and (not in_core):
                    perimeter_indices.append((i, j))

        # Sky-lobby removal set (50% of perimeter modules at sky-lobby levels)
        rng_level = random.Random(seed * 1000003 + L)  # stable per level
        sky_remove = set()
        if L in sky_levels and len(perimeter_indices) > 0:
            k_remove = len(perimeter_indices) // 2
            sky_remove = set(rng_level.sample(perimeter_indices, k_remove))

        # Additional porosity removal on remaining perimeter modules
        remaining_perimeter = [idx for idx in perimeter_indices if idx not in sky_remove]
        poro_remove = set()
        if len(remaining_perimeter) > 0 and p > 0.0:
            k_poro = int(round(p * len(remaining_perimeter)))
            if k_poro > 0:
                poro_remove = set(rng_level.sample(remaining_perimeter, min(k_poro, len(remaining_perimeter))))

        # Compose removal set (perimeter-based)
        perimeter_removal = sky_remove.union(poro_remove)

        # Build boxes
        for (i, j) in all_indices:
            # Keep solid 3x3 core always
            in_core = (abs(i) <= 1 and abs(j) <= 1)
            if (not in_core) and ((i, j) in perimeter_removal):
                continue

            # Module center before transform
            cx = i * module_size
            cy = j * module_size
            cz = bottom_z + 0.5 * module_size
            center_local = Point3d(cx, cy, cz)

            # Evaluate slot culling (world NE and SW) on transformed center
            center_world = center_local
            center_world.Transform(T_level)

            in_slot = False
            if 10 <= L <= 70:
                half = 0.5 * shaft_side_world
                # NE slot: near (+x, +y) corner
                if (center_world.X > (half - slot_w)) and (center_world.Y > (half - slot_w)):
                    in_slot = True
                # SW slot: near (-x, -y) corner
                if (center_world.X < (-half + slot_w)) and (center_world.Y < (-half + slot_w)):
                    in_slot = True
            if in_slot:
                continue

            # Create box in local (unrotated) coordinates and transform to world
            x0 = cx - 0.5 * module_size
            x1 = cx + 0.5 * module_size
            y0 = cy - 0.5 * module_size
            y1 = cy + 0.5 * module_size
            z0 = bottom_z
            z1 = top_z

            box = Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1))
            brep = box.ToBrep()
            if brep is None:
                continue
            brep.Transform(T_level)
            out_breps.append(brep)

    return out_breps"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_tower_geometry(module_size=6.0, total_levels=81, base_modules=10, seed=1)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_tower_geometry(module_size=4.0, total_levels=100, base_modules=11, seed=2025)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_tower_geometry(module_size=5.0, total_levels=96, base_modules=9, seed=42)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
