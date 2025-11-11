""" Summary:
The script defines generate_dangerous_building which assembles cube and sphere Breps to form a volatile façade. For each cube it computes a randomized position and rotation scaled by danger_factor (0–1), seeds randomness for reproducibility, constructs a Box from a bounding box, applies a Z-axis rotation about the cube center, converts it to a Brep, and then places a sphere at the cube's corner. Repeating this per cube yields clustered, offset modules implying instability. The driver calls the function three times with varied counts, sizes, radii, and danger_levels, collects results into lists, and converts them into a Grasshopper DataTree for downstream visualization."""

#! python 3
function_code = """def generate_dangerous_building(cube_count, cube_size, sphere_radius, danger_factor):
    \"""
    Generate a dangerous building composed of cubes and spheres.

    This function creates an architectural geometry that resembles a complex
    and potentially unstable structure using cubes and spheres. The building
    is characterized by a certain level of danger, represented by random
    displacements and rotations of its components.

    Parameters:
    - cube_count (int): The number of cube modules to generate.
    - cube_size (float): The edge length of each cube.
    - sphere_radius (float): The radius of each sphere.
    - danger_factor (float): A factor influencing randomness in placement and
      orientation, between 0 and 1, where 1 is highly disordered.

    Returns:
    - List[Rhino.Geometry.Brep]: A list of Brep geometry representing the building.
    \"""
    import Rhino.Geometry as rg
    import random

    # Ensure the randomness is replicable
    random.seed(42)

    # List to store the resulting geometry
    building_geometry = []

    # Create cubes
    for i in range(cube_count):
        # Random position and rotation to create a "dangerous" effect
        x = random.uniform(-danger_factor * 10, danger_factor * 10)
        y = random.uniform(-danger_factor * 10, danger_factor * 10)
        z = random.uniform(0, danger_factor * 10)
        rotation = random.uniform(0, danger_factor * 90)  # Maximum 90 degrees

        # Create cube as a box
        center = rg.Point3d(x, y, z)
        box = rg.BoundingBox(center, center + rg.Point3d(cube_size, cube_size, cube_size))
        oriented_box = rg.Box(box)
        oriented_box.Transform(rg.Transform.Rotation(rotation, rg.Vector3d.ZAxis, center))

        brep_cube = oriented_box.ToBrep()
        building_geometry.append(brep_cube)

        # Add a sphere at the same position as the cube
        sphere_center = center + rg.Point3d(cube_size / 2, cube_size / 2, cube_size / 2)
        sphere = rg.Sphere(sphere_center, sphere_radius)
        brep_sphere = rg.Brep.CreateFromSphere(sphere)
        building_geometry.append(brep_sphere)

    return building_geometry"""

try:
    exec(function_code)
    import ghpythonlib.treehelpers as th
    from Grasshopper.Kernel.Data import GH_Path
    geometry_states = []
    # Generate sample geometry 1/3
    geometry = generate_dangerous_building(12, 2.0, 0.75, 0.7)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 2/3
    geometry = generate_dangerous_building(8, 1.5, 0.5, 0.9)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Generate sample geometry 3/3
    geometry = generate_dangerous_building(5, 3.5, 1.25, 0.3)
    geometry = list(geometry) if not isinstance(geometry, list) else geometry
    geometry_states.append(geometry)

    # Convert the list of geometries to a Grasshopper DataTree
    geometry_states = th.list_to_tree(geometry_states)

    print("success")
except Exception as e:
    print("Error: ", e)
