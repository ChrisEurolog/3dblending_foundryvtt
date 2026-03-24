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
        print("Usage: blender --background --python blender_unwrap_bake.py -- <high_obj> <low_raw> <high_tex> <output_glb> <max_res> <target_v>")
        sys.exit(1)

    high_poly_obj = argv[0]
    low_poly_raw_obj = argv[1]
    high_poly_tex = argv[2]
    output_glb = argv[3]
    max_res = int(argv[4]) if len(argv) > 4 else 1024
    target_v = int(argv[5]) if len(argv) > 5 else 20000

    # 1. CLEAN SCENE
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    if not os.path.exists(low_poly_raw_obj):
        print(f"Error: Input file {low_poly_raw_obj} does not exist.")
        sys.exit(1)

    # 2. IMPORT HIGH POLY
    print(f"🔹 Importing High-Poly: {high_poly_obj}")
    if not os.path.exists(high_poly_obj):
        print(f"Error: High-poly file {high_poly_obj} does not exist.")
        sys.exit(1)

    bpy.ops.wm.obj_import(
        filepath=high_poly_obj,
        forward_axis='Y',
        up_axis='Z'
    )

    high_poly_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not high_poly_objs:
        print("❌ No mesh objects found in high-poly OBJ.")
        sys.exit(1)

    for obj in high_poly_objs:
        obj.name = "HighPoly_" + obj.name
        obj.hide_render = False # [FIX] Ensure render visibility is ON

    # 3. IMPORT LOW POLY RAW
    print(f"🔹 Importing Low-Poly: {low_poly_raw_obj}")
    bpy.ops.wm.obj_import(
        filepath=low_poly_raw_obj,
        forward_axis='Y',
        up_axis='Z'
    )

    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj not in high_poly_objs]
    if not mesh_objs:
        print("❌ No mesh objects found in low-poly OBJ.")
        sys.exit(1)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    if len(mesh_objs) > 1:
        bpy.ops.object.join()
    low_obj = bpy.context.view_layer.objects.active
    low_obj.name = "LowPoly_Unwrapped"
    low_obj.hide_render = False # [FIX] Ensure render visibility is ON

    # 4. WELD SEAMS AND CLEANUP LOW POLY
    bpy.ops.object.mode_set(mode='EDIT')
    import bmesh
    bm = bmesh.from_edit_mesh(low_obj.data)
    # [FIX] Increased weld distance from 0.0001 to 0.001 to catch Instant Meshes gaps
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001) 
    bmesh.update_edit_mesh(low_obj.data)

    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.mark_sharp(clear=True)
    
    # [FIX] Triangulate the Instant Meshes quads so the UV unwrapper doesn't choke
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

    print("🔹 Obliterating corrupted normals...")
    bpy.ops.mesh.set_normals_from_faces()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 5. UNWRAP LOW POLY
    print("🔹 Auto-Unwrapping UVs...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # [FIX] Changed margin_method to SCALED to prevent fraction UV overlapping in Blender 4.0+
    bpy.ops.uv.smart_project(angle_limit=1.15, margin_method='SCALED', island_margin=0.01)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 6. SMOOTH NORMALS
    print("🔹 Applying smooth shading...")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.shade_smooth()
    
    # [FIX] We must clear the flat custom normals we generated earlier, 
    # otherwise the glTF exporter ignores the shade_smooth() command!
    bpy.context.view_layer.objects.active = low_obj
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass

    # 7. SETUP CYCLES & HIGH POLY MATERIAL
    print("🔹 Setting up Cycles and High-Poly Material...")
    bpy.context.scene.render.engine = 'CYCLES'
    try:
        bpy.context.scene.cycles.device = 'GPU'
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
    except Exception:
        pass 

    high_mat = bpy.data.materials.new(name="HighPoly_Mat")
    high_mat.use_nodes = True
    nodes = high_mat.node_tree.nodes
    nodes.clear() # [FIX] Wipe default nodes to prevent BSDF ghosting

    emission_node = nodes.new('ShaderNodeEmission')
    mat_output = nodes.new('ShaderNodeOutputMaterial')
    high_mat.node_tree.links.new(emission_node.outputs['Emission'], mat_output.inputs['Surface'])

    if high_poly_tex and os.path.exists(high_poly_tex):
        tex_node = nodes.new('ShaderNodeTexImage')
        loaded_image = bpy.data.images.load(high_poly_tex)
        tex_node.image = loaded_image
        high_mat.node_tree.links.new(tex_node.outputs['Color'], emission_node.inputs['Color'])

    for obj in high_poly_objs:
        obj.data.materials.clear()
        obj.data.materials.append(high_mat)

    # 8. LOW POLY MATERIAL SETUP
    print("🔹 Setting up Low-Poly Material for Bake...")
    low_mat = bpy.data.materials.new(name="LowPoly_Mat")
    low_mat.use_nodes = True
    low_nodes = low_mat.node_tree.nodes

    baked_image = bpy.data.images.new(name="Baked_Diffuse", width=max_res, height=max_res, alpha=True)
    bake_tex_node = low_nodes.new('ShaderNodeTexImage')
    bake_tex_node.image = baked_image

    # [FIX] Deselect all other nodes to guarantee target lock
    for node in low_nodes: node.select = False
    bake_tex_node.select = True
    low_nodes.active = bake_tex_node

    low_obj.data.materials.clear()
    low_obj.data.materials.append(low_mat)

    # 9. EXECUTE BAKE
    print("🔹 Executing Cycles Bake...")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in high_poly_objs:
        obj.select_set(True)

    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    try:
        bpy.ops.object.bake(
            type='EMIT',
            use_selected_to_active=True,
            use_cage=True,
            cage_extrusion=0.02, # [FIX] Lowered from 0.1 to 0.02 to prevent crossfire projection
            margin=8,
            margin_type='EXTEND'
        )
        print("✅ Cycles bake complete!")
    except Exception as e:
        print(f"❌ Cycles Bake Error: {e}")
        sys.exit(1)

    # 10. SAVE TEXTURE & APPLY MATTE FINISH
    print("🔹 Saving Texture, Applying Matte Finish and Aligning...")
    actual_baked_png = output_glb.replace('.glb', '_baked.png')
    baked_image.filepath_raw = actual_baked_png
    baked_image.file_format = 'PNG'
    baked_image.save()

    loaded_image = bpy.data.images.load(actual_baked_png)
    loaded_image.pack()
    bake_tex_node.image = loaded_image

    bsdf = next((n for n in low_nodes if n.type == 'BSDF_PRINCIPLED'), None) or low_nodes.get("Principled BSDF") or low_nodes.new('ShaderNodeBsdfPrincipled')

    if 'Base Color' in bsdf.inputs:
        for link in list(bsdf.inputs['Base Color'].links):
            low_mat.node_tree.links.remove(link)

    low_mat.node_tree.links.new(bake_tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value = 0.0
    if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = 0.8
    if 'Coat Weight' in bsdf.inputs: bsdf.inputs['Coat Weight'].default_value = 0.01
    elif 'Coat' in bsdf.inputs: bsdf.inputs['Coat'].default_value = 0.01
    if 'Specular IOR Level' in bsdf.inputs: bsdf.inputs['Specular IOR Level'].default_value = 0.0
    elif 'Specular' in bsdf.inputs: bsdf.inputs['Specular'].default_value = 0.0

    # 11. ATTACH MASTER BASE
    print("🔹 Attaching 'ChrisEurolog3D' Master Base...")
    # Assumes the script runs from your project root. Adjust "assets", "bases" if your folders are named differently!
    base_master_path = os.path.abspath(os.path.join("assets", "bases", "base_master.glb"))

    if os.path.exists(base_master_path):
        bpy.ops.object.select_all(action='DESELECT')
        
        # Import the branded base
        bpy.ops.import_scene.gltf(filepath=base_master_path)
        base_objs = bpy.context.selected_objects
        
        if base_objs:
            base_obj = base_objs[0]
            
            # --- ROBUST POSITIONING FIX (No more hula hoops!) ---
            # Instead of guessing based on Bolar's origin point (his waist),
            # we mathematically calculate his true 'feet' floor.
            print("🔹 Calculating feet position for absolute alignment...")
            bpy.context.view_layer.objects.active = low_obj
            # Must update matrix to get accurate bounding box data after recent imports/merges
            bpy.context.view_layer.update() 
            
            # Use Bounding Box data to find the absolute lowest Vertex Z coordinate.
            # (Works regardless of where the artist put his origin pivot).
            bound_box_z_coords = [v[2] for v in low_obj.bound_box]
            mesh_bottom_z_local = min(bound_box_z_coords)

            # To make Bolar stand exactly ON the ring, we need to lift him.
            # Formula: [Target Base Top (0.05m)] minus [Bolar's Floor offset]
            # Assumes Bolar starts at world Z=0 (which he does on import).
            new_z_lift_distance = 0.05 - mesh_bottom_z_local
            low_obj.location.z = new_z_lift_distance
            print(f"✅ Bolar lifted by {new_z_lift_distance:.3f}m to stand ON the base.")
            # ----------------------------------------------------
            
            # Select both to join them
            bpy.ops.object.select_all(action='DESELECT')
            low_obj.select_set(True)
            base_obj.select_set(True)
            
            # Make the character the active object so the final name remains correct
            bpy.context.view_layer.objects.active = low_obj
            bpy.ops.object.join()
            print("✅ Branded token unified!")
    else:
        print(f"⚠️ Warning: Master base not found at {base_master_path}. Exporting baseless.")

    # 12. EXPORT GLB
    print("🔹 Exporting Final VTT Token...")
    bpy.ops.object.select_all(action='DESELECT')

    for obj in high_poly_objs:
        obj.hide_viewport = True
        obj.hide_render = True
        obj.select_set(False)

    # low_obj now contains both the baked character AND the base
    low_obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_apply=True,
        use_selection=True
    )
    print("✅ Success!")

    bpy.ops.wm.save_as_mainfile(filepath=output_glb.replace('.glb', '_debug.blend'))
    bpy.ops.wm.quit_blender()

if __name__ == "__main__":
    process()
