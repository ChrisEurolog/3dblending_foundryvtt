import bpy
import os
import sys

# Manually add the standard Windows Addon path to sys.path
user_addon_path = os.path.expandvars(r'%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons')
if user_addon_path not in sys.path:
    sys.path.append(user_addon_path)

# Ensure the addon is actually enabled
# Note: Changed from "quad_remesher_1_4" to "quad_remesher"
addon_name = "quad_remesher"

if addon_name not in bpy.context.preferences.addons:
    try:
        bpy.ops.preferences.addon_enable(module=addon_name)
        print(f"✅ {addon_name} successfully enabled.")
    except Exception as e:
        print(f"❌ Could not enable {addon_name}: {e}")

import bmesh
import argparse
import urllib.parse
import json
import struct
import time

MERGE_THRESHOLD = 0.0005

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

# ==========================================
# CLI ARGUMENTS
# ==========================================
def build_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--target", type=int, default=20000)
    p.add_argument("--maxtex", type=int, default=2048)
    p.add_argument("--normalize", type=int, default=1)
    p.add_argument("--matte", type=int, default=1)
    return p

# ==========================================
# PIPELINE EXECUTION
# ==========================================
def finish_export(args, high_obj, low_obj, used_decimate):
    if not low_obj and used_decimate:
        print("❌ Quad Remesher failed to generate mesh. Falling back to Decimate.")
        # Fallback to standard decimation if QR fails in headless mode
        low_obj = high_obj.copy()
        low_obj.data = high_obj.data.copy()
        bpy.context.collection.objects.link(low_obj)
        mod = low_obj.modifiers.new(name="Deci", type='DECIMATE')

        verts_len = len(low_obj.data.vertices)
        if verts_len == 0:
            verts_len = 1
        mod.ratio = max(args.target / verts_len, 0.05)

        mod.use_collapse_triangulate = True

        bpy.ops.object.select_all(action='DESELECT')
        low_obj.select_set(True)
        bpy.context.view_layer.objects.active = low_obj

        bpy.ops.object.modifier_apply(modifier="Deci")

    if not used_decimate:
        # 3. AUTO-UV UNWRAP
        print("🔹 Auto-Unwrapping UVs...")
        bpy.ops.object.select_all(action='DESELECT')
        low_obj.select_set(True)
        bpy.context.view_layer.objects.active = low_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15, margin_method='FRACTION', island_margin=0.01)
        bpy.ops.object.mode_set(mode='OBJECT')

        # 4. HIGH-TO-LOW POLY BAKING
        print(f"🔹 Baking High-Def Textures ({args.maxtex}x{args.maxtex})...")
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'  # Uses GPU if available
        bpy.context.scene.cycles.samples = 1     # 1 sample is perfect for diffuse color

        # Create the blank canvas for the bake
        baked_image = bpy.data.images.new("Baked_Texture", width=args.maxtex, height=args.maxtex)

        # Create the new material for the low-poly token
        baked_mat = bpy.data.materials.new(name="Token_Material")
        baked_mat.use_nodes = True
        low_obj.data.materials.clear()
        low_obj.data.materials.append(baked_mat)

        nodes = baked_mat.node_tree.nodes
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            bsdf = nodes.get("Principled BSDF")
        if bsdf is None:
            bsdf = nodes.new('ShaderNodeBsdfPrincipled')

        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = baked_image
        baked_mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
        nodes.active = tex_node # THIS is critical: Blender bakes to the active image node!

        # Select High, then Low (Low must be active)
        bpy.ops.object.select_all(action='DESELECT')
        high_obj.select_set(True)
        low_obj.select_set(True)
        bpy.context.view_layer.objects.active = low_obj

        # Execute the Bake
        bpy.context.scene.render.bake.use_selected_to_active = True
        bpy.context.scene.render.bake.margin = 16
        bpy.context.scene.render.bake.max_ray_distance = 0.02 # 2cm search radius for details
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})

    # 5. MATTE FINISH & CLEANUP
    print("🔹 Applying Matte Finish and Aligning...")
    bpy.data.objects.remove(high_obj, do_unlink=True) # Destroy the heavy mesh!

    if args.matte == 1:
        # We also want to apply mattening to existing materials on other objects if needed,
        # but in this script, everything is merged and baked to baked_mat
        for mat in bpy.data.materials:
            if mat.use_nodes:
                mat_nodes = mat.node_tree.nodes
                mat_bsdf = next((n for n in mat_nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if mat_bsdf is None:
                    mat_bsdf = mat_nodes.get("Principled BSDF")
                if mat_bsdf:
                    if 'Metallic' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Metallic'].default_value = 0.0
                        for link in mat_bsdf.inputs['Metallic'].links:
                            mat.node_tree.links.remove(link)
                    if 'Roughness' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Roughness'].default_value = 0.8
                        for link in mat_bsdf.inputs['Roughness'].links:
                            mat.node_tree.links.remove(link)

                    if 'Coat Weight' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Coat Weight'].default_value = 0.01
                    elif 'Coat' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Coat'].default_value = 0.01

    # Foundry Floor Alignment
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    verts = list(low_obj.data.vertices)
    if verts:
        bottom_z = min((low_obj.matrix_world @ v.co).z for v in verts)
        low_obj.location.z -= bottom_z
        bpy.ops.object.transform_apply(location=True)

    if args.normalize == 1:
        dims = list(low_obj.dimensions) if hasattr(low_obj.dimensions, '__iter__') else []
        if dims:
            max_dim = max(dims)
            if max_dim > 0:
                scale_factor = 1.0 / max_dim
                low_obj.scale = (scale_factor, scale_factor, scale_factor)
                bpy.ops.object.transform_apply(scale=True)

    # Cleanup pass
    bpy.ops.object.select_all(action='DESELECT')
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.shade_smooth()

    # 6. EXPORT
    print("🔹 Exporting Final VTT Token...")
    bpy.ops.export_scene.gltf(filepath=args.output, export_format='GLB', export_apply=True)
    print("✅ Success!")

    # Hand control back to the caller
    bpy.ops.wm.quit_blender()

def process():
    try:
        idx = sys.argv.index("--")
        argv = sys.argv[idx + 1:]
    except ValueError:
        argv = []

    args = build_args().parse_args(argv)

    # 1. CLEAN SCENE & IMPORT HIGH-POLY
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist.")
        sys.exit(1)
        return

    try:
        validate_gltf_path(args.input)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
        return
    except ValueError as e:
        print(f"Security Error: {e}")
        sys.exit(1)
        return

    bpy.ops.import_scene.gltf(filepath=args.input)

    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objs:
        print("❌ No mesh objects found in GLB.")
        sys.exit(1)
        return

    # Join into a single High-Poly master object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    high_obj = bpy.context.view_layer.objects.active
    high_obj.name = "HighPoly_Master"

    # Clean the High-Poly mesh
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=MERGE_THRESHOLD)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 2. THE SCULPT (Quad Remesher)
    print(f"🔹 Activating Quad Remesher (Target: {args.target} faces)...")
    import addon_utils
    qr_module_name = 'quad_remesher'
    for mod in addon_utils.modules():
        if mod.__name__.startswith('quad_remesher'):
            qr_module_name = mod.__name__
            break

    bpy.ops.preferences.addon_enable(module=qr_module_name)

    # Configure Quad Remesher settings
    bpy.context.scene.qremesher.target_count = args.target
    bpy.context.scene.qremesher.use_materials = False

    # Ensure High Poly is active and selected
    bpy.ops.object.select_all(action='DESELECT')
    high_obj.select_set(True)
    bpy.context.view_layer.objects.active = high_obj

    # Execute Remesh
    used_decimate = False
    low_obj = None

    original_name = bpy.context.active_object.name
    retopo_name = "Retopo_" + original_name

    try:
        bpy.ops.qremesher.remesh()
        print("⏳ Waiting for Exoside engine to finish remeshing...")

        # Wait up to 120 seconds for the new object to appear
        timeout = time.time() + 120

        def check_retopo():
            nonlocal low_obj, used_decimate
            if retopo_name in bpy.data.objects:
                print("✅ Quad Remesher successful!")
                low_obj = bpy.data.objects[retopo_name]
                # Ensure the new object is the active one for the export phase
                bpy.context.view_layer.objects.active = low_obj
                finish_export(args, high_obj, low_obj, used_decimate=False)
                return None

            if time.time() >= timeout:
                print("❌ Quad Remesher timed out waiting for mesh.")
                used_decimate = True
                finish_export(args, high_obj, low_obj=None, used_decimate=True)
                return None

            return 1.0 # Check again in 1 second

        if not hasattr(bpy.app, 'timers'):
            # Fallback for mocking/testing environments without timers
            while time.time() < timeout:
                if retopo_name in bpy.data.objects:
                    low_obj = bpy.data.objects[retopo_name]
                    bpy.context.view_layer.objects.active = low_obj
                    break
                time.sleep(0.5)
            if not low_obj:
                used_decimate = True
            finish_export(args, high_obj, low_obj, used_decimate)
        else:
            bpy.app.timers.register(check_retopo)

    except RuntimeError as e:
        if "expected class QREMESHER_OT_remesh" in str(e):
            print("⚠️ Caught known Quad Remesher cancel bug, continuing pipeline.")
            used_decimate = True
            finish_export(args, high_obj, low_obj=None, used_decimate=True)
        else:
            raise e
    except Exception as e:
        print(f"❌ Error during remeshing: {e}")
        used_decimate = True
        finish_export(args, high_obj, low_obj=None, used_decimate=True)

if __name__ == "__main__":
    process()
