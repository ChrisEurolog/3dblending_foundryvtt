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
    high_poly_tex = argv[2]
    output_glb = argv[3]
    max_res = int(argv[4]) if len(argv) > 4 else 1024
    target_v = int(argv[5]) if len(argv) > 5 else 20000
    
    # Catch the 7th argument (the profile choice from your main menu)
    token_type = str(argv[6]) if len(argv) > 6 else "1"

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
        obj.hide_render = False

    # 3 & 4. GENERATE OR IMPORT LOW POLY
    if token_type == "3":
        print("🔹 Tile Profile Detected: Bypassing Instant Meshes. Using Planar Decimation on High-Poly...")

        bpy.ops.object.select_all(action='DESELECT')
        for obj in high_poly_objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = high_poly_objs[0]
        bpy.ops.object.duplicate()

        mesh_objs = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        bpy.context.view_layer.objects.active = mesh_objs[0]
        if len(mesh_objs) > 1:
            bpy.ops.object.join()

        low_obj = bpy.context.view_layer.objects.active
        low_obj.name = "LowPoly_Unwrapped"
        low_obj.hide_render = False

        bpy.ops.object.modifier_add(type='DECIMATE')
        decimate_mod = low_obj.modifiers["Decimate"]
        decimate_mod.decimate_type = 'DISSOLVE'
        decimate_mod.angle_limit = 0.0872665  # Approx 5 degrees in radians
        bpy.ops.object.modifier_apply(modifier="Decimate")

        bpy.ops.object.modifier_add(type='TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier="Triangulate")

    else:
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
        low_obj.hide_render = False

        bpy.ops.object.mode_set(mode='EDIT')
        import bmesh
        bm = bmesh.from_edit_mesh(low_obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
        bmesh.update_edit_mesh(low_obj.data)

        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.mark_sharp(clear=True)
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

        print("🔹 Obliterating corrupted normals...")
        bpy.ops.mesh.set_normals_from_faces()
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')

    # 5. UNWRAP LOW POLY (Character ONLY - Peak Resolution)
    print("🔹 Auto-Unwrapping UVs...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, margin_method='SCALED', island_margin=0.01)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 6. SMOOTH NORMALS
    print("🔹 Applying smooth shading...")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.shade_smooth()
    
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
    nodes.clear()

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

    bpy.context.view_layer.update()
    
    max_dimension = max(low_obj.dimensions)
    calculated_extrusion = max_dimension * 0.008
    dynamic_extrusion = min(calculated_extrusion, 0.012)
    print(f"🔹 Dynamic Cage Extrusion calculated at: {dynamic_extrusion:.4f}m")

    try:
        bpy.ops.object.bake(
            type='EMIT',
            use_selected_to_active=True,
            use_cage=True,
            cage_extrusion=dynamic_extrusion,
            margin=8,
            margin_type='EXTEND'
        )
        print("✅ Cycles bake complete!")
    except Exception as e:
        print(f"❌ Cycles Bake Error: {e}")
        sys.exit(1)

    # 10. SAVE TEXTURE & APPLY MATTE FINISH
    print("🔹 Saving Texture and Applying Matte Finish...")
    actual_baked_png = output_glb.replace('.glb', '_baked.png')
    baked_image.filepath_raw = actual_baked_png
    baked_image.file_format = 'PNG'
    baked_image.save()

    loaded_image = bpy.data.images.load(actual_baked_png)
    loaded_image.pack()
    bake_tex_node.image = loaded_image

    bsdf = next((n for n in low_nodes if n.type == 'BSDF_PRINCIPLED'), None) or low_nodes.get("Principled BSDF") or low_nodes.new('ShaderNodeBsdfPrincipled')

    if 'Base Color' in bsdf.inputs:
        base_color_input = bsdf.inputs['Base Color']
        while base_color_input.links:
            low_mat.node_tree.links.remove(base_color_input.links[0])

    low_mat.node_tree.links.new(bake_tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value = 0.0
    if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = 0.8
    if 'Coat Weight' in bsdf.inputs: bsdf.inputs['Coat Weight'].default_value = 0.01
    elif 'Coat' in bsdf.inputs: bsdf.inputs['Coat'].default_value = 0.01
    if 'Specular IOR Level' in bsdf.inputs: bsdf.inputs['Specular IOR Level'].default_value = 0.0
    elif 'Specular' in bsdf.inputs: bsdf.inputs['Specular'].default_value = 0.0

    # 11. ATTACH MASTER BASE (POST-BAKE)
    if token_type == "3":
        print("🔹 Profile 3 (Tile/Scenery) selected. Skipping master base attachment.")
        
        print("🔹 Centering prop geometry...")
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

        low_obj.location.x = -center_x
        low_obj.location.y = -center_y
        low_obj.location.z = -mesh_bottom_z_local 
        
    else:
        print(f"🔹 Character Profile ({token_type}) detected. Attaching Master Base...")
        base_master_path = os.path.abspath(os.path.join("assets", "bases", "base_master.glb"))

        if os.path.exists(base_master_path):
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.import_scene.gltf(filepath=base_master_path)
            
            # Identify the newly imported base object
            base_obj = None
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH' and obj != low_obj:
                    base_obj = obj
                    break
            
            if base_obj:
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

                low_obj.location.x = -center_x
                low_obj.location.y = -center_y
                low_obj.location.z = 0.05 - mesh_bottom_z_local
                
                bpy.ops.object.select_all(action='DESELECT')
                low_obj.select_set(True)
                base_obj.select_set(True)
                
                bpy.context.view_layer.objects.active = low_obj
                bpy.ops.object.join()
                print("✅ Master Base attached and token unified!")
        else:
            print(f"⚠️ Warning: Master base not found at {base_master_path}. Exporting baseless.")


    # 12. EXPORT FINAL FILES
    print("🔹 Exporting Final VTT Token and Substance FBX...")
    bpy.ops.object.select_all(action='DESELECT')

    for obj in high_poly_objs:
        obj.hide_viewport = True
        obj.hide_render = True
        obj.select_set(False)

    low_obj.select_set(True)

    # Main GLB Export (Fully textured and ready for VTT)
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_apply=True,
        use_selection=True
    )
    
    # Secondary FBX Export (For optional Substance Painter use)
    output_fbx = output_glb.replace('.glb', '.fbx')
    bpy.ops.export_scene.fbx(
        filepath=output_fbx,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL'
    )
    
    print("✅ Success! Both .glb and .fbx generated.")

    bpy.ops.wm.save_as_mainfile(filepath=output_glb.replace('.glb', '_debug.blend'))
    bpy.ops.wm.quit_blender()

if __name__ == "__main__":
    process()
