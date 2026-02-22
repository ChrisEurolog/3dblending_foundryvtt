import bpy
import os
import argparse
import sys
import bmesh
import json
import struct
import urllib.parse

# Constants
MERGE_THRESHOLD = 0.002

def is_safe_uri(uri):
    """
    Checks if a URI is safe.
    Allowed:
    - Data URIs (data:...)
    - Relative paths without '..' that don't start with '/' or include protocol
    """
    if uri.startswith('data:'):
        return True

    # URL Decode
    decoded_uri = urllib.parse.unquote(uri)

    # Check for absolute paths
    if os.path.isabs(decoded_uri):
        return False

    # Check for protocol usage (e.g., file://, http://) or drive letters (C:/)
    if ':' in decoded_uri:
        return False

    # Check for absolute paths starting with / or \
    if decoded_uri.startswith('/') or decoded_uri.startswith('\\'):
        return False

    # Check for directory traversal
    normalized_path = decoded_uri.replace('\\', '/')
    parts = normalized_path.split('/')
    if '..' in parts:
        return False

    return True

def validate_gltf_path(filepath):
    """
    Validates a glTF/GLB file for external references that could be exploited.
    Raises ValueError if unsafe references are found.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} not found")

    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == '.glb':
            with open(filepath, 'rb') as f:
                # Read header
                magic = f.read(4)
                if magic != b'glTF':
                     raise ValueError("Invalid GLB file: missing magic header")

                version = struct.unpack('<I', f.read(4))[0]
                length = struct.unpack('<I', f.read(4))[0]

                # Read first chunk (JSON)
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
             # Not a glTF/GLB file, skip validation
             return

        # Check for external references
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

def build_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--target", type=int, default=40000)
    p.add_argument("--maxtex", type=int, default=1024)
    p.add_argument("--normalize", type=int, default=1)
    p.add_argument("--matte", type=int, default=1)
    return p

def check_non_manifold(obj):
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()

    bm = bmesh.from_edit_mesh(obj.data)
    is_non_manifold = any(v.select for v in bm.verts) or any(e.select for e in bm.edges)

    bpy.ops.object.mode_set(mode='OBJECT')
    return is_non_manifold

def get_images_from_node_tree(node_tree):
    """Recursively collects images from a node tree, including inside groups."""
    images = set()
    if not node_tree:
        return images

    for node in node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            images.add(node.image)
        elif node.type == 'GROUP' and node.node_tree:
            images.update(get_images_from_node_tree(node.node_tree))

    return images

def resize_textures(max_res, objects=None):
    """
    Iterates through all images in the blend file and scales them down
    if they exceed the max_res dimension.
    If 'objects' is provided, only images used by those objects are checked.
    """
    images_to_check = []

    if objects:
        unique_images = set()
        for obj in objects:
            # Check for material slots (handles both Mesh and Object link types)
            if not hasattr(obj, 'material_slots'):
                continue

            for slot in obj.material_slots:
                mat = slot.material
                if not mat or not mat.use_nodes:
                    continue

                # Recursively traverse node tree
                unique_images.update(get_images_from_node_tree(mat.node_tree))

        # Convert set to list and sort for deterministic order
        images_to_check = sorted(list(unique_images), key=lambda x: x.name)
    else:
        # Fallback: check all images (original behavior)
        images_to_check = bpy.data.images

    print(f"Checking {len(images_to_check)} textures against max resolution: {max_res}px")
    for img in images_to_check:
        if img.size[0] > max_res or img.size[1] > max_res:
            print(f"Resizing {img.name} ({img.size[0]}x{img.size[1]}) -> {max_res}px")
            img.scale(max_res, max_res)

def process():
    # Parse arguments after "--"
    try:
        idx = sys.argv.index("--")
        argv = sys.argv[idx + 1:]
    except ValueError:
        argv = []

    args = build_args().parse_args(argv)

    # 1. CLEAN & IMPORT
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist.")
        sys.exit(1)

    try:
        validate_gltf_path(args.input)
    except ValueError as e:
        print(f"Security Error: {e}")
        return

    bpy.ops.import_scene.gltf(filepath=args.input)

    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objs:
        print("No mesh objects found.")
        return

    # 2. SURGICAL JOIN & UV GLUE
    for obj in mesh_objs:
        if obj.data.uv_layers:
            obj.data.uv_layers[0].name = "UVMap"

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)

    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    active_obj = bpy.context.view_layer.objects.active

    # Glue: Merge by Distance to remove doubles and prevent tearing
    # Reduced threshold to 0.002 (2mm) to fix jagged artifacts from over-merging
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=MERGE_THRESHOLD)
    bpy.ops.object.mode_set(mode='OBJECT')

    # AGENTS.md Rule 2: Check for non-manifold geometry
    # We log it but do not attempt Voxel Remesh to preserve UVs.
    if check_non_manifold(active_obj):
        print(f"Warning: Object {active_obj.name} has non-manifold geometry. Skipping destructive Voxel Remesh.")

    # 3. SMART DECIMATE WITH GUARD RAILS
    current_verts = len(active_obj.data.vertices)
    if args.target > 0 and current_verts > args.target:
        ratio = max(args.target / current_verts, 0.05) # 5% Safety Floor
        mod = active_obj.modifiers.new(name="Deci", type='DECIMATE')
        mod.ratio = ratio
        # AGENTS.md Rule 1: Always use use_collapse_triangulate=True
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="Deci")

    # 4. MATTENING PASS (Blender 5.0)
    if args.matte == 1:
        for mat in bpy.data.materials:
            if mat.use_nodes:
                bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if bsdf:
                    # Handle Blender version differences for property names
                    if 'Coat Weight' in bsdf.inputs:
                        bsdf.inputs['Coat Weight'].default_value = 0.01 # Minimal shine (0.01)
                    elif 'Coat' in bsdf.inputs:
                        bsdf.inputs['Coat'].default_value = 0.01 # Minimal shine (0.01)

                    if 'Roughness' in bsdf.inputs:
                        bsdf.inputs['Roughness'].default_value = 0.8 # Matte base (0.8)

                    if 'Subsurface Weight' in bsdf.inputs:
                        bsdf.inputs['Subsurface Weight'].default_value = 0.0
                    elif 'Subsurface' in bsdf.inputs:
                         bsdf.inputs['Subsurface'].default_value = 0.0

    # 5. FOUNDRY ALIGNMENT (Bottom-Z & Pivot)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Move to Floor
    bottom_z = min((active_obj.matrix_world @ v.co).z for v in active_obj.data.vertices)
    active_obj.location.z -= bottom_z
    bpy.ops.object.transform_apply(location=True)

    # 6. NORMALIZATION
    if args.normalize == 1:
        max_dim = max(active_obj.dimensions)
        if max_dim > 0:
            scale_factor = 1.0 / max_dim
            active_obj.scale = (scale_factor, scale_factor, scale_factor)
            bpy.ops.object.transform_apply(scale=True)

    # 7. TEXTURE RESIZING
    if args.maxtex > 0:
        resize_textures(args.maxtex, objects=[active_obj])

    # AGENTS.md Rule 4: Foundry Compatibility - Normals Consistent
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 8. SHADE SMOOTH & EXPORT
    bpy.ops.object.shade_smooth()
    bpy.ops.export_scene.gltf(filepath=args.output, export_format='GLB', export_apply=True)

if __name__ == "__main__":
    process()
