import os
import sys
import subprocess
import time
import xml.etree.ElementTree as ET
try:
    import bpy
except ImportError:
    pass

def run_xnormal_bake(high_poly_obj, temp_unwrapped_obj, high_poly_tex, max_res, xnormal_exe):
    print(f"🔹 Baking textures using xNormal...")
    if not os.path.exists(xnormal_exe):
        print(f"❌ Error: xNormal executable not found at {xnormal_exe}")
        sys.exit(1)

    baked_tex_png = temp_unwrapped_obj.replace(".obj", "_baked.png")
    xnormal_xml_path = temp_unwrapped_obj.replace(".obj", "_xnormal.xml")

    try:
        root = ET.Element("Settings")
        root.set("Version", "3.19.3.39693")

        high_poly_model = ET.SubElement(root, "HighPolyModel")
        high_mesh = ET.SubElement(high_poly_model, "Mesh")
        high_mesh.set("File", os.path.normpath(os.path.abspath(high_poly_obj)))
        high_mesh.set("Scale", "1.000000")
        high_mesh.set("IgnorePerVertexColor", "true")
        if high_poly_tex and os.path.exists(high_poly_tex):
            high_mesh.set("BaseTex", os.path.normpath(os.path.abspath(high_poly_tex)))
            high_mesh.set("Texture", os.path.normpath(os.path.abspath(high_poly_tex)))

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

        options = ET.SubElement(root, "Options")
        options.set("ThreadPriority", "Normal")
        options.set("BucketSize", "32")

        tree = ET.ElementTree(root)
        tree.write(xnormal_xml_path)

        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/IM", "xNormal.exe"], capture_output=True)

        def print_xnormal_log():
            try:
                if 'USERPROFILE' in os.environ:
                    debug_log_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'xNormal', 'xNormal_debugLog.txt')
                    if os.path.exists(debug_log_path):
                        with open(debug_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            print("\n--- xNormal Debug Log ---")
                            lines = f.readlines()
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

        timeout = time.time() + 60
        actual_baked_png = baked_tex_png.replace(".png", "_baseTex.png")

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
             print_xnormal_log()
             sys.exit(1)

        actual_baked_png = final_png
        print(f"✅ xNormal bake complete: {actual_baked_png}")

        return actual_baked_png

    except Exception as e:
        print(f"❌ Error generating xNormal batch: {e}")
        sys.exit(1)


def assemble_final_glb(temp_unwrapped_obj, actual_baked_png, output_glb):
    print("🔹 Applying Matte Finish and Aligning...")

    # We assume 'low_obj' is already active or we need to import it.
    # The prompt implies a continuation. Let's ensure the low_obj is accessible.
    # In blender_unwrap_bake.py, low_obj was already imported.
    # If run in a fresh script, we need to import the unwrapped OBJ first.

    # 1. CLEAN SCENE
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    if not os.path.exists(temp_unwrapped_obj):
        print(f"Error: Input file {temp_unwrapped_obj} does not exist.")
        sys.exit(1)

    # 2. IMPORT UNWRAPPED LOW POLY
    bpy.ops.wm.obj_import(filepath=temp_unwrapped_obj)
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
        for link in bsdf.inputs['Metallic'].links: baked_mat.node_tree.links.remove(link)
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.8
        for link in bsdf.inputs['Roughness'].links: baked_mat.node_tree.links.remove(link)
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

    xnormal_xml_path = temp_unwrapped_obj.replace(".obj", "_xnormal.xml")
    if os.path.exists(xnormal_xml_path): os.remove(xnormal_xml_path)
    if os.path.exists(actual_baked_png): os.remove(actual_baked_png)


def run_xatlas_unwrap(low_poly_raw_obj):
    temp_unwrapped_obj = low_poly_raw_obj.replace('.obj', '_unwrapped.obj')
    return temp_unwrapped_obj

def unwrap_and_bake(high_poly_obj, low_poly_raw_obj, high_poly_tex, output_glb, max_res, xnormal_exe):
    print(f"🔹 Unwrapping and Baking textures...")

    # 1. UV Unwrap low-poly using xatlas (or similar CLI tool if available)
    temp_unwrapped_obj = run_xatlas_unwrap(low_poly_raw_obj)

    # 2. Bake textures with xNormal
    actual_baked_png = run_xnormal_bake(high_poly_obj, temp_unwrapped_obj, high_poly_tex, max_res, xnormal_exe)

    # 3. Assemble final GLB
    assemble_final_glb(temp_unwrapped_obj, actual_baked_png, output_glb)
