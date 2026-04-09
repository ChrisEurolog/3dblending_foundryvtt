import bpy
import os
import sys

def process():
    try:
        idx = sys.argv.index("--")
        argv = sys.argv[idx + 1:]
    except ValueError:
        argv = []

    if len(argv) < 4:
        print("Usage: blender --background --python blender_unwrap_bake.py -- <high_obj> <low_raw> <high_tex> <output_glb> <max_res> <target_v> <token_type>")
        sys.exit(1)

    high_poly_obj = argv[0]
    low_poly_raw_obj = argv[1]
    # high_poly_tex = argv[2]  <-- IGNORED in Substance Pipeline
    output_glb = argv[3]
    # max_res = int(argv[4])   <-- IGNORED in Substance Pipeline
    target_v = int(argv[5]) if len(argv) > 5 else 20000
    token_type = str(argv[6]) if len(argv) > 6 else "1"

    # 1. CLEAN SCENE
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # 2. GET BASE GEOMETRY
    if token_type == "3":
        print(f"🔹 Tile Profile Detected: Importing High-Poly for Decimation...")
        if not os.path.exists(high_poly_obj):
            print(f"Error: High-poly file {high_poly_obj} does not exist.")
            sys.exit(1)

        bpy.ops.wm.obj_import(filepath=high_poly_obj, forward_axis='Y', up_axis='Z')
        mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']

        bpy.context.view_layer.objects.active = mesh_objs[0]
        if len(mesh_objs) > 1:
            bpy.ops.object.join()

        low_obj = bpy.context.view_layer.objects.active
        low_obj.name = "LowPoly_Unwrapped"

        # Decimate & Triangulate
        bpy.ops.object.modifier_add(type='DECIMATE')
        low_obj.modifiers["Decimate"].decimate_type = 'DISSOLVE'
        low_obj.modifiers["Decimate"].angle_limit = 0.0872665
        bpy.ops.object.modifier_apply(modifier="Decimate")

        bpy.ops.object.modifier_add(type='TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier="Triangulate")

    else:
        print(f"🔹 Character Profile Detected: Importing Instant Meshes Output...")
        if not os.path.exists(low_poly_raw_obj):
            print(f"Error: Input file {low_poly_raw_obj} does not exist.")
            sys.exit(1)

        bpy.ops.wm.obj_import(filepath=low_poly_raw_obj, forward_axis='Y', up_axis='Z')
        mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']

        bpy.context.view_layer.objects.active = mesh_objs[0]
        if len(mesh_objs) > 1:
            bpy.ops.object.join()
        low_obj = bpy.context.view_layer.objects.active
        low_obj.name = "LowPoly_Unwrapped"

        # Weld Seams and Cleanup
        bpy.ops.object.mode_set(mode='EDIT')
        import bmesh
        bm = bmesh.from_edit_mesh(low_obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
        bmesh.update_edit_mesh(low_obj.data)

        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.mark_sharp(clear=True)
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

        bpy.ops.mesh.set_normals_from_faces()
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')

    # 3. UNWRAP LOW POLY
    print("🔹 Auto-Unwrapping UVs for Substance Painter...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Increased island margin specifically for Substance Painter edge-padding
    bpy.ops.uv.smart_project(angle_limit=1.15, margin_method='SCALED', island_margin=0.05)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 4. SMOOTH NORMALS
    bpy.ops.object.shade_smooth()
    bpy.context.view_layer.objects.active = low_obj
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass 

    # 5. ASSIGN BLANK MATERIAL
    print("🔹 Assigning clean Substance Material...")
    blank_mat = bpy.data.materials.new(name="Substance_Mat")
    low_obj.data.materials.clear()
    low_obj.data.materials.append(blank_mat)

    # 6. ATTACH MASTER BASE OR CENTER
    if token_type == "3":
        print("🔹 Centering prop geometry...")
        bpy.context.view_layer.update() 
        bound_z = [v[2] for v in low_obj.bound_box]
        mesh_bottom_z_local = min(bound_z)

        vertices = low_obj.data.vertices
        total_verts = len(vertices)
        if total_verts > 0:
            center_x = sum(v.co.x for v in vertices) / total_verts
            center_y = sum(v.co.y for v in vertices) / total_verts
        else:
            center_x, center_y = 0.0, 0.0

        low_obj.location.x = -center_x
        low_obj.location.y = -center_y
        low_obj.location.z = -mesh_bottom_z_local 
    else:
        print("🔹 Attaching Master Base...")
        base_master_path = os.path.abspath(os.path.join("assets", "bases", "base_master.glb"))

        if os.path.exists(base_master_path):
            bpy.ops.import_scene.gltf(filepath=base_master_path)
            base_objs = [obj for obj in bpy.context.selected_objects if obj != low_obj]

            if base_objs:
                base_obj = base_objs[0]

                bpy.context.view_layer.objects.active = low_obj
                bpy.context.view_layer.update() 

                bound_z = [v[2] for v in low_obj.bound_box]
                mesh_bottom_z_local = min(bound_z)

                vertices = low_obj.data.vertices
                total_verts = len(vertices)
                if total_verts > 0:
                    center_x = sum(v.co.x for v in vertices) / total_verts
                    center_y = sum(v.co.y for v in vertices) / total_verts
                else:
                    center_x, center_y = 0.0, 0.0

                # Lift to stand on the 0.05m base
                low_obj.location.x = -center_x
                low_obj.location.y = -center_y
                low_obj.location.z = 0.05 - mesh_bottom_z_local

                bpy.ops.object.select_all(action='DESELECT')
                low_obj.select_set(True)
                base_obj.select_set(True)

                bpy.context.view_layer.objects.active = low_obj
                bpy.ops.object.join()
        else:
            print(f"⚠️ Warning: Master base not found at {base_master_path}. Exporting baseless.")

    # 7. EXPORT FOR SUBSTANCE
    print("🔹 Exporting Clean Files for Substance Painter...")
    bpy.ops.object.select_all(action='DESELECT')
    low_obj.select_set(True)

    # Main export for CE3D master pipeline (GLB)
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_apply=True,
        use_selection=True
    )

    # NEW: Secondary FBX export specifically for Substance Painter
    output_fbx = output_glb.replace('.glb', '.fbx')
    bpy.ops.export_scene.fbx(
        filepath=output_fbx,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL'
    )

    print(f"✅ Success! FBX and GLB ready for texturing.")
    bpy.ops.wm.quit_blender()

if __name__ == "__main__":
    process()