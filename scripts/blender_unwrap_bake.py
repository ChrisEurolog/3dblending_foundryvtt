import bpy
import os
import sys
import xml.etree.ElementTree as ET
import subprocess

def process():
    try:
        idx = sys.argv.index("--")
        argv = sys.argv[idx + 1:]
    except ValueError:
        argv = []

    if len(argv) < 5:
        print("Usage: blender --background --python blender_unwrap_bake.py -- <high_obj> <low_raw> <high_tex> <output_glb> <xnormal_exe> <max_res> <target_v>")
        sys.exit(1)

    high_poly_obj = argv[0]
    low_poly_raw_obj = argv[1]
    high_poly_tex = argv[2]
    output_glb = argv[3]
    xnormal_exe = argv[4]
    max_res = int(argv[5]) if len(argv) > 5 else 1024
    target_v = int(argv[6]) if len(argv) > 6 else 20000

    # 1. CLEAN SCENE
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    if not os.path.exists(low_poly_raw_obj):
        print(f"Error: Input file {low_poly_raw_obj} does not exist.")
        sys.exit(1)

    # 2. IMPORT LOW POLY RAW
    bpy.ops.wm.obj_import(filepath=low_poly_raw_obj)

    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not mesh_objs:
        print("❌ No mesh objects found in low-poly OBJ.")
        sys.exit(1)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    low_obj = bpy.context.view_layer.objects.active
    low_obj.name = "LowPoly_Unwrapped"

    # 4. UNWRAP LOW POLY
    print("🔹 Auto-Unwrapping UVs...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Smart project with 89 degree limit (~1.55 radians) to minimize fragmentation and maximize contiguous texel density
    bpy.ops.uv.smart_project(angle_limit=1.55, margin_method='FRACTION', island_margin=0.03)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 5. SMOOTH NORMALS
    bpy.ops.object.shade_smooth()

    # 6. EXPORT UNWRAPPED OBJ FOR XNORMAL
    temp_unwrapped_obj = low_poly_raw_obj.replace(".obj", "_uv.obj")

    bpy.ops.object.select_all(action='DESELECT')
    low_obj.select_set(True)

    bpy.ops.wm.obj_export(
        filepath=temp_unwrapped_obj,
        export_selected_objects=True,
        export_materials=False,
        apply_modifiers=True,
        export_normals=True,
        export_uv=True
    )
    print(f"✅ Exported unwrapped low-poly OBJ to {temp_unwrapped_obj}")

    # 7. BAKE TEXTURES WITH XNORMAL CLI
    print(f"🔹 Baking textures using xNormal...")
    if not os.path.exists(xnormal_exe):
        print(f"❌ Error: xNormal executable not found at {xnormal_exe}")
        sys.exit(1)

    baked_tex_png = temp_unwrapped_obj.replace(".obj", "_baked.png")
    xnormal_xml_path = temp_unwrapped_obj.replace(".obj", "_xnormal.xml")

    try:
        # Construct xNormal batch XML matching xNormal 3.19.3 schema
        # Reference: xNormal requires exact casing and specific tags like <xNormal>, not <Settings>.
        # PascalCase XML tags and attributes for xNormal batch settings.
        # Ensure root tag is Settings.
        root = ET.Element("Settings")
        root.set("Version", "3.19.3.39693")

        high_poly_model = ET.SubElement(root, "HighPolyModel")
        high_mesh = ET.SubElement(high_poly_model, "Mesh")
        high_mesh.set("File", os.path.normpath(os.path.abspath(high_poly_obj)))
        high_mesh.set("Scale", "1.000000")
        high_mesh.set("IgnorePerVertexColor", "true")
        if high_poly_tex and os.path.exists(high_poly_tex):
            high_mesh.set("BaseTexture", os.path.normpath(os.path.abspath(high_poly_tex)))

        low_poly_model = ET.SubElement(root, "LowPolyModel")
        low_mesh = ET.SubElement(low_poly_model, "Mesh")
        low_mesh.set("File", os.path.normpath(os.path.abspath(temp_unwrapped_obj)))
        low_mesh.set("Scale", "1.000000")
        low_mesh.set("MaxRayDistanceFront", "0.050000")
        low_mesh.set("MaxRayDistanceBack", "0.050000")
        low_mesh.set("MatchUV", "true")

        generation = ET.SubElement(root, "GenerateMaps")
        generation.set("Width", str(max_res))
        generation.set("Height", str(max_res))
        generation.set("EdgePadding", "16")
        generation.set("File", os.path.normpath(os.path.abspath(baked_tex_png)))
        generation.set("AA", "4")
        generation.set("GenNormals", "false")
        generation.set("GenAO", "false")
        generation.set("BakeHighpolyBaseTex", "true")

        # Add Options block which xNormal batch processor expects
        options = ET.SubElement(root, "Options")
        options.set("ThreadPriority", "Normal")
        options.set("BucketSize", "32")

        # Write XML
        tree = ET.ElementTree(root)
        tree.write(xnormal_xml_path)

        # Terminate any lingering GUI instances of xNormal which cause the batch process to hang or crash
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/IM", "xNormal.exe"], capture_output=True)

        def print_xnormal_log():
            try:
                # xNormal outputs its debug log to the user's Documents folder
                if 'USERPROFILE' in os.environ:
                    debug_log_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'xNormal', 'xNormal_debugLog.txt')
                    if os.path.exists(debug_log_path):
                        with open(debug_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            print("\n--- xNormal Debug Log ---")
                            lines = f.readlines()
                            # Print the last 50 lines to ensure we catch the error reason
                            print("".join(lines[-50:]))
                            print("-------------------------")
                    else:
                        print(f"\n--- No xNormal debug log found at {debug_log_path} ---")
            except Exception as ex:
                print(f"\n--- Could not read xNormal debug log: {ex} ---")

        print(f"🔹 xNormal Batch XML generated at: {xnormal_xml_path}")
        print("--- xNormal XML Configuration ---")
        try:
            with open(xnormal_xml_path, 'r') as xml_file:
                print(xml_file.read())
        except Exception:
            print("Could not read XML file to console.")
        print("---------------------------------")

        # Execute xNormal
        # Note: xNormal CLI usually returns immediately while rendering in a background process,
        # but in batch mode it can be blocking depending on flags.
        try:
            result = subprocess.run(
                [xnormal_exe, xnormal_xml_path],
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ xNormal bake complete")
        except subprocess.CalledProcessError as e:
            print(f"❌ xNormal Engine Error: {e}")
            if e.stdout: print("STDOUT:\n", e.stdout)
            if e.stderr: print("STDERR:\n", e.stderr)
            print_xnormal_log()
            sys.exit(1)

        # Wait for texture to be generated if process exited early
        import time
        timeout = time.time() + 60
        actual_baked_png = baked_tex_png.replace(".png", "_baseTex.png")

        # xNormal handles "File" differently sometimes depending on internal logic. Check multiple variants.
        possible_outputs = [
            actual_baked_png,
            baked_tex_png,
            baked_tex_png.replace(".png", "_base.png"),
            baked_tex_png.replace(".png", "_baseTexBaked.png")
        ]

        final_png = None
        while time.time() < timeout:
            for p in possible_outputs:
                if os.path.exists(p) and os.path.getsize(p) > 0:
                    final_png = p
                    break
            if final_png:
                break
            time.sleep(1)

        if not final_png:
             print(f"❌ xNormal timeout: Could not locate baked texture at {actual_baked_png}")

             # Fallback debug log parser
             print_xnormal_log()

             sys.exit(1)

        actual_baked_png = final_png
        print(f"✅ xNormal bake complete: {actual_baked_png}")

    except Exception as e:
        print(f"❌ Error generating xNormal batch: {e}")
        sys.exit(1)

    # 8. LOAD TEXTURE & APPLY MATTE FINISH
    print("🔹 Applying Matte Finish and Aligning...")

    baked_mat = bpy.data.materials.new(name="Token_Material")
    baked_mat.use_nodes = True

    nodes = baked_mat.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None) or nodes.get("Principled BSDF") or nodes.new('ShaderNodeBsdfPrincipled')
    tex_node = nodes.new('ShaderNodeTexImage')

    loaded_image = bpy.data.images.load(actual_baked_png)
    loaded_image.pack()
    tex_node.image = loaded_image
    nodes.active = tex_node
    tex_node.select = True

    baked_mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = 0.0
        for link in list(bsdf.inputs['Metallic'].links): baked_mat.node_tree.links.remove(link)
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.8
        for link in list(bsdf.inputs['Roughness'].links): baked_mat.node_tree.links.remove(link)
    if 'Coat Weight' in bsdf.inputs:
        bsdf.inputs['Coat Weight'].default_value = 0.01
    elif 'Coat' in bsdf.inputs:
        bsdf.inputs['Coat'].default_value = 0.01
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.0

    low_obj.data.materials.clear()
    low_obj.data.materials.append(baked_mat)

    # 9. EXPORT GLB
    print("🔹 Exporting Final VTT Token...")
    bpy.ops.object.select_all(action='DESELECT')
    low_obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_apply=True,
        use_selection=True
    )
    print("✅ Success!")

    # Cleanup
    if os.path.exists(temp_unwrapped_obj): os.remove(temp_unwrapped_obj)
    if os.path.exists(xnormal_xml_path): os.remove(xnormal_xml_path)
    if os.path.exists(actual_baked_png): os.remove(actual_baked_png)

    bpy.ops.wm.quit_blender()

if __name__ == "__main__":
    process()
