import bpy
import os
import sys
import urllib.parse
import json
import struct

# ==========================================
# SECURITY & VALIDATION
# ==========================================
def is_safe_uri(uri):
    if uri.startswith('data:'):
        return True
    decoded_uri = urllib.parse.unquote(uri)
    if os.path.isabs(decoded_uri):
        return False
    if ':' in decoded_uri:
        return False
    if decoded_uri.startswith('/') or decoded_uri.startswith('\\'):
        return False
    if '..' in decoded_uri.replace('\\', '/').split('/'):
        return False
    return True

def validate_gltf_path(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} not found")

    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == '.glb':
            with open(filepath, 'rb') as f:
                magic = f.read(4)
                if magic != b'glTF':
                     raise ValueError("Invalid GLB file: missing magic header")

                version = struct.unpack('<I', f.read(4))[0]
                length = struct.unpack('<I', f.read(4))[0]

                chunk_length = struct.unpack('<I', f.read(4))[0]
                chunk_type = f.read(4)

                if chunk_type != b'JSON':
                     raise ValueError("Invalid GLB file: first chunk is not JSON")

                json_data = f.read(chunk_length)
                try:
                    data = json.loads(json_data)
                except json.JSONDecodeError:
                    raise ValueError("Invalid GLB file: JSON chunk is malformed")

        elif ext == '.gltf':
             with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    raise ValueError("Invalid glTF file: JSON is malformed")
        else:
             return True

        if 'buffers' in data:
            for buffer in data['buffers']:
                if 'uri' in buffer:
                    uri = buffer['uri']
                    if not is_safe_uri(uri):
                        raise ValueError(f"Unsafe buffer URI detected: {uri}")

        if 'images' in data:
            for image in data['images']:
                if 'uri' in image:
                    uri = image['uri']
                    if not is_safe_uri(uri):
                         raise ValueError(f"Unsafe image URI detected: {uri}")

    except Exception as e:
        raise ValueError(f"Failed to validate glTF file: {e}")

    return True

def process():
    try:
        idx = sys.argv.index("--")
        argv = sys.argv[idx + 1:]
    except ValueError:
        argv = []

    if len(argv) < 2:
        print("Usage: blender --background --python blender_extract.py -- <input_glb> <output_obj> [target_vertices]")
        sys.exit(1)

    input_glb = argv[0]
    output_obj = argv[1]

    target_verts = int(argv[2]) if len(argv) > 2 else 100000

    # 1. CLEAN SCENE & VALIDATE
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    if not os.path.exists(input_glb):
        print(f"Error: Input file {input_glb} does not exist.")
        sys.exit(1)

    try:
        validate_gltf_path(input_glb)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Security Error: {e}")
        sys.exit(1)

    # 2. IMPORT GLB
    bpy.ops.import_scene.gltf(filepath=input_glb)

    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objs:
        print("❌ No mesh objects found in GLB.")
        sys.exit(1)

    # Join into a single High-Poly master object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    if len(mesh_objs) > 1:
        bpy.ops.object.join()
    high_obj = bpy.context.view_layer.objects.active
    high_obj.name = "HighPoly_Master"

    # We MUST weld vertices! GLBs split vertices at every UV seam.
    # If we don't weld first, decimation will rip the mesh into a shattered polygon soup,
    # and recalculating normals on an unwelded mesh will cause erratic, flipped normal bakes.
    bpy.ops.object.mode_set(mode='EDIT')
    import bmesh
    bm = bmesh.from_edit_mesh(high_obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bmesh.update_edit_mesh(high_obj.data)

    # Ensure consistent normals
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Important: Clear custom split normals inherited from the GLB
    # Welding vertices severely mangles existing custom split normals, causing shattered/black texture bakes.
    # Do not use customdata_custom_splitnormals_clear() here without try/except as it causes a fatal exception in Blender 5.0+
    # when the custom data layer doesn't exist.
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass

    # Smooth normals
    bpy.ops.object.shade_smooth()

    # Normalize origin and scale
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    high_obj.location = (0, 0, 0)
    bpy.context.view_layer.update()

    dims = list(high_obj.dimensions) if hasattr(high_obj.dimensions, '__iter__') else []
    if dims:
        max_dim = max(dims)
        if max_dim > 0:
            scale_factor = 1.0 / max_dim
            high_obj.scale = (scale_factor, scale_factor, scale_factor)

    # Make sure we select the object and set it active before applying transforms
    # Sometimes joining or origin sets might mess up selection context
    bpy.ops.object.select_all(action='DESELECT')
    high_obj.select_set(True)
    bpy.context.view_layer.objects.active = high_obj

    # Force apply all transformations (Location, Rotation, Scale) to the mesh data
    # This prevents the 90 degree X rotation from Meshy GLBs from being interpreted incorrectly later
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Force an update of the view layer to ensure transforms are locked
    bpy.context.view_layer.update()

    # 3. EXPORT TEXTURE
    # Find the base color texture to extract
    output_tex = output_obj.replace(".obj", "_diffuse.png")
    texture_exported = False

    for mat in high_obj.data.materials:
        if mat and mat.use_nodes:
            mat_nodes = mat.node_tree.nodes
            mat_bsdf = next((n for n in mat_nodes if n.type == 'BSDF_PRINCIPLED'), None) or mat_nodes.get("Principled BSDF")

            if mat_bsdf:
                base_color_input = mat_bsdf.inputs.get('Base Color')
                if base_color_input and base_color_input.is_linked:
                    link = base_color_input.links[0]
                    if link.from_node.type == 'TEX_IMAGE' and link.from_node.image:
                        img = link.from_node.image

                        # Save the image to the specified path
                        old_filepath = img.filepath_raw
                        img.filepath_raw = output_tex
                        img.file_format = 'PNG'
                        img.save()

                        img.filepath_raw = old_filepath # restore just in case
                        texture_exported = True
                        print(f"✅ Extracted diffuse texture to {output_tex}")
                        break

    if not texture_exported:
        print("⚠️ No base color texture found in high-poly material.")

    # 4. EXPORT ORIGINAL HIGH POLY (FOR BAKING)
    bpy.ops.object.select_all(action='DESELECT')
    high_obj.select_set(True)

    bpy.ops.wm.obj_export(
        filepath=output_obj,
        export_selected_objects=True,
        export_materials=False,
        apply_modifiers=True,
        export_normals=True,
        export_uv=True,
        forward_axis='Y',
        up_axis='Z'
    )
    print(f"✅ Exported high-poly OBJ to {output_obj}")

    # 5. DECIMATE AND EXPORT SCULPT OBJ (FOR INSTANT MESHES)
    # Decimate the high-poly mesh down to the target vertices before passing to Instant Meshes
    # This prevents Instant Meshes from choking on 800k+ vertex inputs and failing to hit the target,
    # while leaving the original 800k mesh untouched on disk for xNormal to bake from.

    verts_len = max(len(high_obj.data.vertices), 1)
    if verts_len > target_verts:
        print(f"🔹 Decimating sculpt mesh from {verts_len} down to {target_verts} for Instant Meshes processing...")
        mod = high_obj.modifiers.new(name="Deci", type='DECIMATE')
        mod.ratio = max(target_verts / verts_len, 0.05)
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="Deci")

        # Repair fractured geometry caused by decimation
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(high_obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        bmesh.update_edit_mesh(high_obj.data)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')

        try:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except Exception:
            pass

    sculpt_obj_path = output_obj.replace(".obj", "_sculpt.obj")

    bpy.ops.wm.obj_export(
        filepath=sculpt_obj_path,
        export_selected_objects=True,
        export_materials=False,
        apply_modifiers=True,
        export_normals=True,
        export_uv=False, # UVs not needed for sculpt retopology
        forward_axis='Y',
        up_axis='Z'
    )
    print(f"✅ Exported decimated sculpt OBJ to {sculpt_obj_path}")

    bpy.ops.wm.quit_blender()

if __name__ == "__main__":
    process()
