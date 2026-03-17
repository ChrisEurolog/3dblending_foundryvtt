import sys
import argparse
import subprocess
import os
import xml.etree.ElementTree as ET

def unwrap_and_bake(high_poly_obj, low_poly_raw_obj, high_poly_tex, output_glb, max_res, xnormal_exe):
    print(f"🔹 Unwrapping and Baking textures...")

    # 1. UV Unwrapping with xatlas
    print(f"🔹 Unwrapping {low_poly_raw_obj} with xatlas...")
    try:
        import trimesh
        import xatlas

        mesh = trimesh.load(low_poly_raw_obj, force='mesh')

        # Use Atlas to configure padding and prevent texture bleed across UV seams
        atlas = xatlas.Atlas()
        atlas.add_mesh(mesh.vertices, mesh.faces)

        pack_options = xatlas.PackOptions()
        pack_options.padding = 8 # Provide enough pixel padding between UV islands

        atlas.generate(pack_options=pack_options)
        vmapping, indices, uvs = atlas[0]

        vertices = mesh.vertices[vmapping]

        unwrapped_mesh = trimesh.Trimesh(vertices=vertices, faces=indices, process=False)
        unwrapped_mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)

        temp_unwrapped_obj = low_poly_raw_obj.replace(".obj", "_uv.obj")
        unwrapped_mesh.export(temp_unwrapped_obj)
        # Ensure no invalid .mtl file is passed to xNormal, which causes "can't find a plugin for" errors
        mtl_file = temp_unwrapped_obj.replace('.obj', '.mtl')
        if os.path.exists(mtl_file):
            os.remove(mtl_file)

        print(f"✅ Unwrapped mesh saved to {temp_unwrapped_obj}")

    except Exception as e:
        print(f"❌ Error during xatlas UV unwrapping: {e}")
        return False

    # 2. Baking with xNormal CLI
    print(f"🔹 Baking textures using xNormal...")
    if not os.path.exists(xnormal_exe):
        print(f"❌ Error: xNormal executable not found at {xnormal_exe}")
        return False

    baked_tex_png = temp_unwrapped_obj.replace(".obj", "_baked.png")
    xnormal_xml_path = temp_unwrapped_obj.replace(".obj", "_xnormal.xml")

    try:
        # Construct xNormal batch XML matching the schema provided by the user (v3.19.3)
        root = ET.Element("Settings")
        root.set("Version", "3.19.3")

        high_poly_model = ET.SubElement(root, "HighPolyModel")
        high_mesh = ET.SubElement(high_poly_model, "Mesh")
        high_mesh.set("File", os.path.normpath(os.path.abspath(high_poly_obj)))
        high_mesh.set("Scale", "1.000000")
        high_mesh.set("IgnorePerVertexColor", "true") # Force texture usage over vertex colors

        if high_poly_tex and os.path.exists(high_poly_tex):
            # Based on standard xNormal XML configurations
            high_mesh.set("BaseTexture", os.path.normpath(os.path.abspath(high_poly_tex)))
            high_mesh.set("Texture", os.path.normpath(os.path.abspath(high_poly_tex)))

        low_poly_model = ET.SubElement(root, "LowPolyModel")
        low_mesh = ET.SubElement(low_poly_model, "Mesh")
        low_mesh.set("File", os.path.normpath(os.path.abspath(temp_unwrapped_obj)))
        low_mesh.set("Scale", "1.000000")
        # Ray distances must be small for a 1.0 unit model. A distance of 2.0
        # causes rays to pass through the entire model, mapping the back of the model
        # to the front (shattered appearance with black ray misses).
        low_mesh.set("MaxRayDistanceFront", "0.050000")
        low_mesh.set("MaxRayDistanceBack", "0.050000")

        # In the native Settings XML, the baking element is GenerateMaps
        generation = ET.SubElement(root, "GenerateMaps")
        generation.set("BakeHighpolyBaseTex", "true") # Bake Albedo/Diffuse
        generation.set("BakeBaseColor", "true") # Add fallback attribute
        # Set missing ray color to black to prevent glaring red cracks
        generation.set("BackgroundColor", "0,0,0")
        generation.set("GenNormals", "false")
        generation.set("GenAO", "false")
        generation.set("Width", str(max_res))
        generation.set("Height", str(max_res))
        generation.set("EdgePadding", "32") # Increased to 32 to prevent bleeding/tearing around UV seams

        # Output file mapping: In xNormal batch configurations, the generic output path
        # for GenerateMaps is mapped via the File attribute. xNormal will use this prefix
        # and automatically append the generated map's suffix (e.g. _baseTex.png).
        generation.set("File", os.path.normpath(os.path.abspath(baked_tex_png)))

        # Ensure antialiasing is turned on for high quality
        generation.set("AA", "4")

        # Write XML
        tree = ET.ElementTree(root)
        tree.write(xnormal_xml_path)

        # Kill any existing xNormal processes to prevent hanging
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/IM', 'xNormal.exe'], capture_output=True, check=False)
        except Exception as e:
            pass

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
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print("❌ xNormal execution failed!")

            # xNormal is a GUI app and often logs errors to a specific debug file rather than stderr
            debug_log = os.path.expanduser(r'~\Documents\xNormal\xNormal_debugLog.txt')
            if os.path.exists(debug_log):
                print("--- xNormal Debug Log ---")
                try:
                    with open(debug_log, 'r', encoding='utf-8', errors='ignore') as f:
                        print(f.read())
                except Exception as log_e:
                    print(f"Could not read debug log: {log_e}")
                print("-------------------------")
            else:
                print(f"--- xNormal stdout ---\n{e.stdout}")
                print(f"--- xNormal stderr ---\n{e.stderr}")
            return False

        actual_baked_png = baked_tex_png
        if not os.path.exists(actual_baked_png):
            # xNormal appends a suffix like _baseTex or _base_color to the File path
            import glob
            base_name = os.path.splitext(baked_tex_png)[0]
            matches = glob.glob(f"{base_name}*.png")
            if matches:
                actual_baked_png = matches[0]
            else:
                print("❌ xNormal failed to generate the baked texture. No output file found.")
                return False

        print(f"✅ xNormal bake complete: {actual_baked_png}")

    except Exception as e:
        print(f"❌ Error during xNormal setup/baking: {e}")
        return False

    # 3. Assemble final GLB
    print(f"🔹 Assembling final GLB to {output_glb}...")
    try:
        from PIL import Image
        # Load the baked texture
        baked_image = Image.open(actual_baked_png)

        # Load the unwrapped mesh and apply the texture
        final_mesh = trimesh.load(temp_unwrapped_obj, force='mesh')
        mat = trimesh.visual.material.PBRMaterial(baseColorTexture=baked_image,
                                                 metallicFactor=0.0,
                                                 roughnessFactor=0.8) # Apply matte finish here

        final_mesh.visual = trimesh.visual.TextureVisuals(uv=final_mesh.visual.uv, material=mat)

        # Create a scene and export
        scene = trimesh.Scene(final_mesh)
        scene.export(output_glb)
        print("✅ GLB Assembly complete!")

        # Cleanup
        if os.path.exists(temp_unwrapped_obj): os.remove(temp_unwrapped_obj)
        if os.path.exists(xnormal_xml_path): os.remove(xnormal_xml_path)
        if os.path.exists(actual_baked_png): os.remove(actual_baked_png)

        return True

    except Exception as e:
        print(f"❌ Error assembling GLB: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UV Unwrap and Bake Textures (xNormal)")
    parser.add_argument("--high_obj", required=True, help="High poly OBJ file")
    parser.add_argument("--low_raw", required=True, help="Low poly raw OBJ file from Instant Meshes")
    parser.add_argument("--high_tex", required=False, help="High poly diffuse texture file", default=None)
    parser.add_argument("--output_glb", required=True, help="Output GLB file")
    parser.add_argument("--max_res", type=int, default=1024, help="Max texture resolution")
    parser.add_argument("--xnormal_exe", required=True, help="Path to xNormal executable")

    args = parser.parse_args()
    unwrap_and_bake(args.high_obj, args.low_raw, args.high_tex, args.output_glb, args.max_res, args.xnormal_exe)
