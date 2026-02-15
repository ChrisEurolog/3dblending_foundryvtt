import bpy
import os
import argparse
import sys
import bmesh

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

def resize_textures(max_res):
    """
    Iterates through all images in the blend file and scales them down
    if they exceed the max_res dimension.
    """
    print(f"Checking textures against max resolution: {max_res}px")
    for img in bpy.data.images:
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
    # This replaces Voxel Remesh which destroys UVs
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001) # 1mm threshold
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
                        bsdf.inputs['Coat Weight'].default_value = 0.05 # Was 0.2, then 0.0, now 0.05 for subtle shine
                    elif 'Coat' in bsdf.inputs:
                        bsdf.inputs['Coat'].default_value = 0.05 # Was 0.2, then 0.0, now 0.05 for subtle shine

                    if 'Roughness' in bsdf.inputs:
                        bsdf.inputs['Roughness'].default_value = 0.8 # Was 0.5

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
        resize_textures(args.maxtex)

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
