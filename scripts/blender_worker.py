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

MERGE_THRESHOLD = 0.0001

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
                except (json.JSONDecodeError, EOFError):
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
# PIPELINE EXECUTION HELPER FUNCTIONS
# ==========================================
def apply_decimate_fallback(args, high_obj, low_obj):
    print("❌ Quad Remesher failed to generate mesh. Falling back to Decimate.")
    low_obj = high_obj.copy()
    low_obj.data = high_obj.data.copy()
    bpy.context.collection.objects.link(low_obj)
    mod = low_obj.modifiers.new(name="Deci", type='DECIMATE')
    verts_len = max(len(low_obj.data.vertices), 1)
    mod.ratio = max(args.target / verts_len, 0.05)
    mod.use_collapse_triangulate = True
    bpy.ops.object.select_all(action='DESELECT')
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj
    bpy.ops.object.modifier_apply(modifier="Deci")
    return low_obj

def clean_and_unwrap_geometry(low_obj):
    # 1. FIX THE FBX IMPORT DATA
    print("🔹 Cleaning Quad Remesher FBX geometry...")
    bpy.ops.object.select_all(action='DESELECT')
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Weld exact overlapping vertices from FBX seam splits
    import bmesh
    bm = bmesh.from_edit_mesh(low_obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_THRESHOLD)
    bmesh.update_edit_mesh(low_obj.data)

    bpy.ops.mesh.customdata_custom_splitnormals_clear() # UNLOCK THE NORMALS
    bpy.ops.mesh.mark_sharp(clear=True) # Clear explicit sharp edges so shade_smooth works properly across FBX seams
        # bpy.ops.mesh.normals_make_consistent(inside=False) # Omitted per user override to prevent lighting shards
    bpy.ops.object.mode_set(mode='OBJECT')

    # Now that normals are unlocked, this will actually smooth the surface for the bake!
    bpy.ops.object.shade_smooth()

    # 2. AUTO-UV UNWRAP
    print("🔹 Auto-Unwrapping UVs...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Smart project with 89 degree limit (~1.55 radians) to minimize fragmentation and maximize contiguous texel density
    bpy.ops.uv.smart_project(angle_limit=1.55, margin_method='FRACTION', island_margin=0.03)
    bpy.ops.object.mode_set(mode='OBJECT')

def prepare_materials_for_bake(high_obj):
    # 2.5 PREPARE HIGH-POLY FOR EMIT BAKE
    print("🔹 Converting High-Poly materials to Emission for pure Albedo bake...")
    for mat in high_obj.data.materials:
        if mat and mat.use_nodes:
            mat_nodes = mat.node_tree.nodes
            mat_bsdf = next((n for n in mat_nodes if n.type == 'BSDF_PRINCIPLED'), None) or mat_nodes.get("Principled BSDF")
            mat_output = next((n for n in mat_nodes if n.type == 'OUTPUT_MATERIAL'), None) or mat_nodes.get("Material Output")

            if mat_bsdf and mat_output:
                # Create emission node to bypass all PBR lighting/metallic issues during bake
                emit_node = mat_nodes.new('ShaderNodeEmission')

                # See if anything is connected to Base Color
                base_color_input = mat_bsdf.inputs.get('Base Color')
                if base_color_input and base_color_input.is_linked:
                    link = base_color_input.links[0]
                    mat.node_tree.links.new(link.from_socket, emit_node.inputs['Color'])
                else:
                    emit_node.inputs['Color'].default_value = base_color_input.default_value if base_color_input else (1.0, 1.0, 1.0, 1.0)

                # Connect emission directly to output
                mat.node_tree.links.new(emit_node.outputs['Emission'], mat_output.inputs['Surface'])

def bake_textures(args, high_obj, low_obj):
    # 3. HIGH-TO-LOW POLY BAKING
    # Bake at a higher resolution (e.g. 2x) then scale down, or simply use the requested resolution
    # We bake natively at the target resolution to avoid downsampling artifacts (bilinear interpolation)
    # which can bleed unrendered background pixels into the edges of UV islands causing tearing/seams.
    bake_res = args.maxtex
    print(f"🔹 Baking High-Def Textures directly at ({bake_res}x{bake_res}) to avoid interpolation tearing...")
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'
    bpy.context.scene.cycles.samples = 16

    baked_image = bpy.data.images.new("Baked_Texture", width=bake_res, height=bake_res)
    baked_mat = bpy.data.materials.new(name="Token_Material")
    baked_mat.use_nodes = True

    nodes = baked_mat.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None) or nodes.get("Principled BSDF") or nodes.new('ShaderNodeBsdfPrincipled')
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = baked_image
    nodes.active = tex_node
    tex_node.select = True

    # We removed the ShaderNodeUVMap here because unconfigured UV maps break the glTF exporter.
    # The exporter will automatically use the active UV map for the ShaderNodeTexImage.

    high_obj.hide_viewport = False
    high_obj.hide_set(False)

    low_obj.data.materials.clear()
    low_obj.data.materials.append(baked_mat)

    bpy.ops.object.select_all(action='DESELECT')
    high_obj.select_set(True)
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    bpy.context.scene.render.bake.use_selected_to_active = True


    # Extrude the ray-cast origin outward by 3% of the 1.0 unit model scale
    # to ensure rays begin *outside* any high-poly bulging geometry (belts, beards).
    # Set max_ray_distance to cast deep enough inward to hit recessed areas.
    bpy.context.scene.render.bake.cage_extrusion = 0.03
    bpy.context.scene.render.bake.max_ray_distance = 0.05

    # Explicitly configure the diffuse bake to ONLY capture the Base Color (Albedo).
    # Without disabling Direct and Indirect lighting, the headless bake will evaluate the scene's
    # actual lighting (which is zero) and output a black/grey image.
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True

    try:
        # Bake EMIT to capture pure Albedo bypassing all lighting and PBR calculations
        bpy.ops.object.bake(type='EMIT', use_selected_to_active=True, margin=8, margin_type='EXTEND')
    except Exception as e:
        print(f"❌ Bake Error: {e}")
        bpy.ops.wm.quit_blender()

    # Save the baked image to a temporary file IN THE SAME DIRECTORY as the output GLB.
    # This is CRITICAL for the headless glTF exporter because it cannot resolve relative paths
    # from the OS temp directory when the .blend file is unsaved, causing it to drop the texture entirely.
    # Saving as PNG prevents lossy JPEG compression artifacts along sharp UV edges, resolving "tearing".
    out_dir = os.path.dirname(os.path.abspath(args.output))
    temp_img_path = os.path.join(out_dir, f"Baked_Texture_{int(time.time())}.png")
    baked_image.filepath_raw = temp_img_path
    baked_image.file_format = 'PNG'

    baked_image.save()
    print(f"🔹 Saved baked texture to temporary path: {temp_img_path}")

    # Now re-load it from disk to ensure it behaves exactly like an external texture for glTF export
    loaded_image = bpy.data.images.load(temp_img_path)

    # Force the loaded image to be packed into the current blend file memory.
    # This guarantees the glTF exporter embeds it, bypassing any external path resolution issues.
    loaded_image.pack()
    tex_node.image = loaded_image

    # Link the texture AFTER baking to prevent circular dependency errors
    baked_mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    return temp_img_path

def apply_matte_and_align(args, high_obj, low_obj):
    # 4. MATTE FINISH & ALIGNMENT
    print("🔹 Applying Matte Finish and Aligning...")
    # Safely hide the high-poly so it doesn't export
    high_obj.select_set(False)
    high_obj.hide_viewport = True
    high_obj.hide_render = True

    if args.matte == 1:
        for mat in low_obj.data.materials:
            if mat.use_nodes:
                mat_nodes = mat.node_tree.nodes
                mat_bsdf = next((n for n in mat_nodes if n.type == 'BSDF_PRINCIPLED'), None) or mat_nodes.get("Principled BSDF")
                if mat_bsdf:
                    if 'Metallic' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Metallic'].default_value = 0.0
                        for link in list(mat_bsdf.inputs['Metallic'].links): mat.node_tree.links.remove(link)
                    if 'Roughness' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Roughness'].default_value = 0.8
                        for link in list(mat_bsdf.inputs['Roughness'].links): mat.node_tree.links.remove(link)
                    if 'Coat Weight' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Coat Weight'].default_value = 0.01
                    elif 'Coat' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Coat'].default_value = 0.01

                    # Force Specular to 0.0 to prevent any default shininess!
                    if 'Specular IOR Level' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Specular IOR Level'].default_value = 0.0
                    elif 'Specular' in mat_bsdf.inputs:
                        mat_bsdf.inputs['Specular'].default_value = 0.0

    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    verts = low_obj.data.vertices
    if len(verts) > 0:
        mw = low_obj.matrix_world
        bottom_z = min((mw @ v.co).z for v in verts)
        low_obj.location.z -= bottom_z
        bpy.ops.object.transform_apply(location=True)

# ==========================================
# PIPELINE EXECUTION
# ==========================================
def finish_export(args, high_obj, low_obj, used_decimate):
    temp_img_path = None
    if not low_obj and used_decimate:
        low_obj = apply_decimate_fallback(args, high_obj, low_obj)

    if not used_decimate:
        clean_and_unwrap_geometry(low_obj)
        prepare_materials_for_bake(high_obj)
        temp_img_path = bake_textures(args, high_obj, low_obj)

    apply_matte_and_align(args, high_obj, low_obj)

    # 5. EXPORT
    print("🔹 Exporting Final VTT Token...")
    bpy.ops.object.select_all(action='DESELECT')
    low_obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=args.output,
        export_format='GLB',
        export_apply=True,
        use_selection=True
    )
    print("✅ Success!")

    if temp_img_path and os.path.exists(temp_img_path):
        try:
            os.remove(temp_img_path)
            print(f"🔹 Cleaned up temporary texture: {temp_img_path}")
        except Exception as e:
            print(f"⚠️ Failed to remove temporary texture: {e}")

    bpy.ops.wm.quit_blender()

def import_high_poly(args):
    # 1. CLEAN SCENE & IMPORT HIGH-POLY
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist.")
        sys.exit(1)

    try:
        validate_gltf_path(args.input)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Security Error: {e}")
        sys.exit(1)

    bpy.ops.import_scene.gltf(filepath=args.input)

    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objs:
        print("❌ No mesh objects found in GLB.")
        sys.exit(1)

    # Join into a single High-Poly master object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    high_obj = bpy.context.view_layer.objects.active
    high_obj.name = "HighPoly_Master"

    return high_obj

def prepare_remesh(args, high_obj):
    # --- JULES: INSERT SURGICAL FIX HERE ---
    # Ensure HighPoly_Master has consistent normals
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    if args.normalize == 1:
        # Center the origin and normalize to exactly 1.0 unit
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        high_obj.location = (0, 0, 0)

        # Force a dependency graph update to ensure dimensions are accurate after the origin change
        bpy.context.view_layer.update()

        dims = list(high_obj.dimensions) if hasattr(high_obj.dimensions, '__iter__') else []
        if dims:
            max_dim = max(dims)
            if max_dim > 0:
                scale_factor = 1.0 / max_dim
                high_obj.scale = (scale_factor, scale_factor, scale_factor)

        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # ---------------------------------------

    # Check for non-manifold geometry and harden it with Voxel Remesh if needed
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    import bmesh
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)

    # Analyze non-manifold edges
    non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
    has_non_manifold = len(non_manifold_edges) > 0
    verts_before = len(bm.verts)

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"🔹 Preserving all {verts_before} high-poly vertices for baking.")

    # Create a hardened duplicate specifically for Quad Remesher to process
    # This prevents the original high-poly from losing UVs/Textures needed for baking
    harden_obj = high_obj.copy()
    harden_obj.data = high_obj.data.copy()
    bpy.context.collection.objects.link(harden_obj)
    harden_obj.name = "HighPoly_Hardened"

    if has_non_manifold:
        print(f"⚠️ Non-manifold geometry detected ({len(non_manifold_edges)} edges). Hardening geometry via Voxel Remesh...")
        bpy.context.view_layer.objects.active = harden_obj
        mod = harden_obj.modifiers.new(name="VoxelRemesh", type='REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = 0.005 # Detailed enough for a 1.0 unit model
        bpy.ops.object.modifier_apply(modifier="VoxelRemesh")

    return harden_obj

def execute_quad_remesher(args, high_obj, harden_obj):
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
    # Since Quad Remesher interprets target as quads (2 triangles), and
    # glTF inherently splits vertices at UV seams, we divide by 2 to prevent overshooting the target
    bpy.context.scene.qremesher.target_count = max(args.target // 2, 100)
    bpy.context.scene.qremesher.use_materials = False

    # Attempt to disable normal/hard-edge splitting to prevent shattered geometry
    if hasattr(bpy.context.scene.qremesher, 'use_normals'):
        bpy.context.scene.qremesher.use_normals = False
    if hasattr(bpy.context.scene.qremesher, 'use_normals_splitting'):
        bpy.context.scene.qremesher.use_normals_splitting = False

    # Ensure Hardened Object is active and selected for Quad Remesher
    bpy.ops.object.select_all(action='DESELECT')
    harden_obj.select_set(True)
    bpy.context.view_layer.objects.active = harden_obj

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
            status, low_obj_out, decimate_out = check_retopo_logic(
                retopo_name, harden_obj, timeout, time.time, bpy.data.objects, bpy.context
            )

            if status == 'SUCCESS':
                low_obj = low_obj_out
                used_decimate = decimate_out
                finish_export(args, high_obj, low_obj, used_decimate)
                return None
            elif status == 'TIMEOUT':
                used_decimate = decimate_out
                finish_export(args, high_obj, low_obj=None, used_decimate=used_decimate)
                return None
            else:
                return 1.0  # Check again in 1 second

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
                bpy.data.objects.remove(harden_obj, do_unlink=True)
            finish_export(args, high_obj, low_obj, used_decimate)
        else:
            bpy.app.timers.register(check_retopo)

    except RuntimeError as e:
        bpy.data.objects.remove(harden_obj, do_unlink=True)
        if "expected class QREMESHER_OT_remesh" in str(e):
            print("⚠️ Caught known Quad Remesher cancel bug, continuing pipeline.")
            used_decimate = True
            finish_export(args, high_obj, low_obj=None, used_decimate=True)
        else:
            raise e
    except Exception as e:
        bpy.data.objects.remove(harden_obj, do_unlink=True)
        print(f"❌ Error during remeshing: {e}")
        used_decimate = True
        finish_export(args, high_obj, low_obj=None, used_decimate=True)

def process():
    try:
        idx = sys.argv.index("--")
        argv = sys.argv[idx + 1:]
    except ValueError:
        argv = []

    args = build_args().parse_args(argv)

    high_obj = import_high_poly(args)
    harden_obj = prepare_remesh(args, high_obj)
    execute_quad_remesher(args, high_obj, harden_obj)

if __name__ == "__main__":
    process()