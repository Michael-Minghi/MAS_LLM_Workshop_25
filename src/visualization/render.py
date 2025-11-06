import bpy
import os
from mathutils import Vector
from enum import StrEnum
import math

class RenderStyle(StrEnum):
    SOLID = "render_material_solid"  # Render with solid color
    GHOSTED = "render_material_ghost"  # Render with ghosted effect (outline)
    HATCH = "render_material_hatch"  # Render in hatch mode

# BLENDER ENV
design_collection_name = "DESIGNS"  # Main parent collection containing sub-collections
scene_collection_name = "SCENE"  # Collection with the sun, camera, etc.
hidden_collection_name = "HIDDEN"  # Collection containing objects to be hidden

def render_objs(
    paths=None,
    resolution_x=1080,
    resolution_y=1080,
    scale_local=True,
    animation=False,
    frames=120,
    render_style=RenderStyle.GHOSTED,
    file_suffix="",
    y_up=False,
):
    def create_collection(name: str, hidden=False):
        if name in bpy.data.collections:
            collection = bpy.data.collections.get(name)
            remove_obj_and_collection(collection=collection)
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        if hidden:
            collection.hide_viewport = True
        return collection

    def remove_obj_and_collection(collection):
        for obj in collection.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in collection.children:
            remove_obj_and_collection(child)
        bpy.data.collections.remove(collection, do_unlink=True)

    def import_objs(paths):
        # Remove all user collections except SCENE and HIDDEN
        for collection in bpy.data.collections:
            if collection.name not in ("SCENE", "HIDDEN"):
                print(f"remove all objs in collection {collection.name}")
                remove_obj_and_collection(collection)

        # Create a main collection named DESIGNS
        designs_collection = create_collection(design_collection_name, hidden=False)

        # Import each .obj
        for i, path in enumerate(paths):
            print(path)
            if y_up:
                bpy.ops.wm.obj_import(filepath=path, forward_axis="Z", up_axis="Y")
            else:
                bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z")

            # Rename objects after import
            for j, obj in enumerate(bpy.context.selected_objects):
                obj.name = f"{i}_{j}_model"

            # Move imported objects to DESIGNS collection
            imported_objects = [obj for obj in bpy.context.selected_objects]
            for obj in imported_objects:
                bpy.context.scene.collection.objects.unlink(obj)
                designs_collection.objects.link(obj)

            print(f"Imported {os.path.basename(path)}")

        # Remove default collection if empty
        default_collection = bpy.data.collections.get("Collection")
        if default_collection and len(default_collection.objects) == 0:
            bpy.data.collections.remove(default_collection)

    def add_keyframe(obj, frames):
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = frames
        for frame in range(1, frames + 1):
            # Rotate object in Z axis
            obj.rotation_euler[2] = (frame / frames) * 2 * math.pi
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    # 1) Import objects
    import_objs(paths)
    print("Batch import completed!")

    # Fetch essential collections
    scene_collection = bpy.data.collections.get(scene_collection_name)
    hidden_collection = bpy.data.collections.get(hidden_collection_name)
    design_collection = bpy.data.collections.get(design_collection_name)

    # Attempt to grab a Grease Pencil object and its first modifier
    mod = None
    for obj in bpy.data.objects:
        if obj.type == "GREASEPENCIL":
            mod = obj.modifiers.get("outline_mod")
            break

    # Ensure SCENE collection is rendered if needed
    if scene_collection:
        scene_collection.hide_render = False

    # Hide objects in HIDDEN collection
    if hidden_collection:
        for obj in hidden_collection.objects:
            obj.hide_render = True
    else:
        print(f"Collection '{hidden_collection_name}' not found!")

    # Compute reference dimension from placeholderbox
    ref_box = bpy.data.objects.get("placeholderbox")
    if not ref_box:
        print("No placeholderbox found! Using reference dimension = 1.")
        ref_dim = 1.0
    else:
        ref_bbox = [Vector(corner) for corner in ref_box.bound_box]
        ref_dim = max([corner.x for corner in ref_bbox]) - min([corner.x for corner in ref_bbox])

    # Adjust import objects' bounding boxes and scale
    scale_factors = []
    if design_collection:
        for obj in design_collection.objects:
            bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            xs, ys, zs = [c.x for c in bbox], [c.y for c in bbox], [c.z for c in bbox]
            bound = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

            # Move obj to bounding box center
            obj.location.x -= (bound[0] + bound[1]) / 2
            obj.location.y -= (bound[2] + bound[3]) / 2
            obj.location.z -= bound[4]
            print(f"Moved {obj.name} to world center.")

            largest_dim = max((bound[1] - bound[0]), (bound[3] - bound[2]), (bound[5] - bound[4]))
            scale_factors.append(ref_dim / largest_dim)

        # Scale objects
        overall_scale = min(scale_factors) if not scale_local else None

        # Place at world origin
        bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)

        for obj, sf in zip(design_collection.objects, scale_factors):
            if overall_scale is not None:
                # Use the smallest scale factor for all
                sf = overall_scale

            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="BOUNDS")
            obj.select_set(False)
            obj.scale *= sf
            print (f"Scaled {obj.name} by factor {sf:.2f}.")

    # Set resolution
    scene = bpy.context.scene
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y

    # 2) For final rendering, hide all first
    if design_collection:
        for obj in design_collection.objects:
            obj.hide_render = True

        # 3) Render each object individually
        for i, obj in enumerate(design_collection.objects):

            src_dir = os.path.dirname(paths[i])

            # Build filename
            base_parts = os.path.basename(src_dir).split("_")
            obj_id = int(os.path.basename(paths[i]).split("_")[0])
            base_parts.insert(3, f"{obj_id + 1:04}")
            final_basename = "_".join(base_parts)

            # STILL + ANIMATION Filenames
            y_up_suffix = "_Y-up" if y_up else ""
            final_still_path = os.path.join(src_dir, f"{final_basename}{file_suffix}{y_up_suffix}.png")
            temp_still_path = os.path.join(src_dir, f"{final_basename}{file_suffix}{y_up_suffix}_temp_still.png")
            final_anim_path = os.path.join(src_dir, f"{final_basename}{file_suffix}{y_up_suffix}.mp4")
            temp_anim_path = os.path.join(src_dir, f"{final_basename}{file_suffix}{y_up_suffix}_temp") # + ".mp4")

            # Unhide this object
            obj.hide_render = False

            # set render material
            material = bpy.data.materials.get(render_style.value)
            if material:
                obj.data.materials.clear()
                obj.data.materials.append(material)

            # set object outline 
            if mod:
                mod.source_object = obj

            bpy.context.scene.cycles.device = 'GPU'
            # --- 1) Render the STILL image first ---
            if os.path.exists(final_still_path):
                print(f"Skipping object {obj.name}, still image already exists.")
            else:
                bpy.context.scene.render.image_settings.file_format = "PNG"
                bpy.context.scene.render.filepath = temp_still_path
                bpy.context.scene.cycles.samples = 300
                bpy.ops.render.render(write_still=True)

                if os.path.exists(temp_still_path):
                    os.rename(temp_still_path, final_still_path)
                    print(f"Saved still as {final_still_path}")

            # --- 2) Then render the ANIMATION (if requested) ---
            if animation:
                if os.path.exists(final_anim_path):
                    print(f"Skipping object {obj.name}, animation video already exists.")
                else:
                    add_keyframe(obj, frames)
                    bpy.context.scene.render.image_settings.file_format = "FFMPEG"
                    bpy.context.scene.render.ffmpeg.format = "MPEG4"
                    bpy.context.scene.render.ffmpeg.codec = "H264"
                    # Turn off frame numbering so the final file is just "filename.mp4"
                    bpy.context.scene.render.use_file_extension = True
                    # bpy.context.scene.render.use_frame_number_ext = False
                    bpy.ops.render.render(animation=True)

                    bpy.context.scene.render.filepath = temp_anim_path
                    # bpy.context.scene.render.filepath = "C:\\Users\\team\\Documents\\Anton\\test"
                    bpy.context.scene.cycles.samples = 200
                    
                    bpy.ops.render.render(write_still=True, animation=True)
                    start_frame = 1
                    guessed_output = f"{temp_anim_path}{start_frame:04d}-{frames:04d}.mp4"
                    # final_output   = f"{path_no_ext}.mp4"

                    if os.path.exists(guessed_output):
                        os.rename(guessed_output, final_anim_path)
                        print(f"Saved animation as {final_anim_path}")

            # Hide again
            obj.hide_render = True


def parse_folder(dir):
    paths = []
    last_dir = None
    temp = []
    for dir_path, dir_names, file_names in os.walk(dir):
        
        for file in file_names:
            if file.endswith(".obj"):
                if not last_dir:
                    last_dir = dir_path

                if dir_path == last_dir:
                    temp.append(os.path.join(dir_path, file))
                else:
                    last_dir = dir_path
                    paths.append(temp)
                    temp = [os.path.join(dir_path, file)]
    paths.append(temp)
    return paths


def parse_text(dir, src):
    with open(dir, "r") as fp:
        lines = fp.readlines()
        print(lines[:10])
        # Convert each line to an absolute path and keep directory portion
        paths = [os.path.dirname(os.path.join(src, line)) for line in lines]
        print(paths[:10])
        all_paths = []
        for p in paths:
            found_objs = parse_folder(os.path.join(src, p))
            all_paths.append(found_objs)
        return all_paths


if __name__ == "__main__":
    # # Render selected object from a text file
    # FOLDER = os.path.join(os.path.dirname(bpy.data.filepath), "render_selection.txt")
    # src = os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    # paths = parse_text(FOLDER, src)

    # Render all objects from a folder
    output_dir = os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath)))
    paths = parse_folder(os.path.join(output_dir, 'output', 'designs'))

    for m in paths:
        render_objs(
            m,
            resolution_x=512,
            resolution_y=512,
            scale_local=True,
            animation=False,
            file_suffix="",
            render_style=RenderStyle.SOLID,
            y_up=False,
        )
