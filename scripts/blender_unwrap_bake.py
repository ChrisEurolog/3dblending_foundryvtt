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

    # 3. WELD SEAMS AND CLEANUP LOW POLY
    bpy.ops.object.mode_set(mode='EDIT')
    import bmesh
    bm = bmesh.from_edit_mesh(low_obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bmesh.update_edit_mesh(low_obj.data)

    # Select all again just to be safe
    bpy.ops.mesh.select_all(action='SELECT')
    # Un-mark any sharp edges that might have come through Instant Meshes
    bpy.ops.mesh.mark_sharp(clear=True)
    # Recalculate normals outwards to guarantee consistency before xNormal raycasting
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Important: Do not use customdata_custom_splitnormals_clear() here as it causes a fatal exception in Blender 5.0+
    # when the custom data layer doesn't exist.
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass

    # 4. UNWRAP LOW POLY
    print("🔹 Auto-Unwrapping UVs...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Smart project with 89 degree limit (~1.55 radians) to minimize fragmentation and maximize contiguous texel density
    bpy.ops.uv.smart_project(angle_limit=1.55, margin_method='FRACTION', island_margin=0.05)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 6. SMOOTH NORMALS
    bpy.ops.object.shade_smooth()

    # 7. SETUP CYCLES & HIGH POLY MATERIAL
    print("🔹 Setting up Cycles and High-Poly Material...")
    bpy.context.scene.render.engine = 'CYCLES'
    try:
        bpy.context.scene.cycles.device = 'GPU'
        # Enable GPU compute if available
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA' # Or 'OPTIX'/'HIP'/'METAL' depending on system, but CUDA is safest default fallback next to CPU
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
    except Exception:
        pass # Fallback to CPU is handled natively by Blender if GPU fails

    # Create Material for High Poly
    high_mat = bpy.data.materials.new(name="HighPoly_Mat")
    high_mat.use_nodes = True
    nodes = high_mat.node_tree.nodes

    # Use Emission for bake source to avoid light transport issues
    emission_node = nodes.new('ShaderNodeEmission')

    # Get the material output node
    mat_output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not mat_output:
        mat_output = nodes.new('ShaderNodeOutputMaterial')

    # Link Emission to Material Output
    high_mat.node_tree.links.new(emission_node.outputs['Emission'], mat_output.inputs['Surface'])

    if high_poly_tex and os.path.exists(high_poly_tex):
        tex_node = nodes.new('ShaderNodeTexImage')
        loaded_image = bpy.data.images.load(high_poly_tex)
        tex_node.image = loaded_image

        # Link Texture directly to Emission Color
        high_mat.node_tree.links.new(tex_node.outputs['Color'], emission_node.inputs['Color'])

    for obj in high_poly_objs:
        obj.data.materials.clear()
        obj.data.materials.append(high_mat)

    # 8. LOW POLY MATERIAL SETUP
    print("🔹 Setting up Low-Poly Material for Bake...")
    low_mat = bpy.data.materials.new(name="LowPoly_Mat")
    low_mat.use_nodes = True
    low_nodes = low_mat.node_tree.nodes

    # Create the image we'll bake to
    baked_image = bpy.data.images.new(name="Baked_Diffuse", width=max_res, height=max_res, alpha=True)

    # Create Image Texture node for the Low Poly Material
    bake_tex_node = low_nodes.new('ShaderNodeTexImage')
    bake_tex_node.image = baked_image

    # Select node and make it active (CRUCIAL FOR BAKING)
    bake_tex_node.select = True
    low_nodes.active = bake_tex_node

    low_obj.data.materials.clear()
    low_obj.data.materials.append(low_mat)

    # 9. EXECUTE BAKE
    print("🔹 Executing Cycles Bake...")
    bpy.ops.object.select_all(action='DESELECT')
    for obj in high_poly_objs:
        obj.select_set(True)

    # Active object is the target of the bake
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    try:
        bpy.ops.object.bake(
            type='EMIT',
            use_selected_to_active=True,
            cage_extrusion=0.02,
            max_ray_distance=0.05,
            margin=8,
            margin_type='EXTEND'
        )
        print("✅ Cycles bake complete!")
    except Exception as e:
        print(f"❌ Cycles Bake Error: {e}")
        sys.exit(1)

    # 10. SAVE TEXTURE & APPLY MATTE FINISH
    print("🔹 Saving Texture, Applying Matte Finish and Aligning...")

    # Save the baked image to disk and pack it so glTF exporter embeds it
    actual_baked_png = output_glb.replace('.glb', '_baked.png')
    baked_image.filepath_raw = actual_baked_png
    baked_image.file_format = 'PNG'
    baked_image.save()

    # Reload and pack as required by glTF exporter memory rule
    loaded_image = bpy.data.images.load(actual_baked_png)
    loaded_image.pack()
    bake_tex_node.image = loaded_image

    bsdf = next((n for n in low_nodes if n.type == 'BSDF_PRINCIPLED'), None) or low_nodes.get("Principled BSDF") or low_nodes.new('ShaderNodeBsdfPrincipled')

    # Clear any existing links to Base Color
    if 'Base Color' in bsdf.inputs:
        for link in list(bsdf.inputs['Base Color'].links):
            low_mat.node_tree.links.remove(link)

    low_mat.node_tree.links.new(bake_tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = 0.0
        for link in list(bsdf.inputs['Metallic'].links): low_mat.node_tree.links.remove(link)
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.8
        for link in list(bsdf.inputs['Roughness'].links): low_mat.node_tree.links.remove(link)
    if 'Coat Weight' in bsdf.inputs:
        bsdf.inputs['Coat Weight'].default_value = 0.01
    elif 'Coat' in bsdf.inputs:
        bsdf.inputs['Coat'].default_value = 0.01
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.0

    # 11. EXPORT GLB
    print("🔹 Exporting Final VTT Token...")
    bpy.ops.object.select_all(action='DESELECT')

    # Hide the High-Poly mesh completely
    for obj in high_poly_objs:
        obj.hide_viewport = True
        obj.hide_render = True
        obj.select_set(False)

    low_obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_apply=True,
        use_selection=True
    )
    print("✅ Success!")

    # Cleanup
    # Kept raw _baked.png file for diagnostic inspection
    # if os.path.exists(actual_baked_png): os.remove(actual_baked_png)

    bpy.ops.wm.save_as_mainfile(filepath=output_glb.replace('.glb', '_debug.blend'))
    bpy.ops.wm.quit_blender()

if __name__ == "__main__":
    process()
