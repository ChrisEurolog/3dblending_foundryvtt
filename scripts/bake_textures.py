import sys
import argparse
import subprocess
import os
import xml.etree.ElementTree as ET

def unwrap_and_bake(high_poly_obj, low_poly_raw_obj, output_glb, max_res, xnormal_exe):
    print(f"🔹 Unwrapping and Baking textures...")

    # 1. UV Unwrapping with xatlas
    print(f"🔹 Unwrapping {low_poly_raw_obj} with xatlas...")
    try:
        import trimesh
        import xatlas

        mesh = trimesh.load(low_poly_raw_obj, force='mesh')

        vmapping, indices, uvs = xatlas.parametrize(mesh.vertices, mesh.faces)
        vertices = mesh.vertices[vmapping]

        unwrapped_mesh = trimesh.Trimesh(vertices=vertices, faces=indices, process=False)
        unwrapped_mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)

        temp_unwrapped_obj = low_poly_raw_obj.replace(".obj", "_uv.obj")
        unwrapped_mesh.export(temp_unwrapped_obj)
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
        # Construct xNormal batch XML according to the official xNormal schema
        # xNormal uses an XML file passed via CLI for batch processing: xNormal.exe path_to_xml.xml
        root = ET.Element("xNormal")

        high_poly_model = ET.SubElement(root, "HighPolyModel")
        high_mesh = ET.SubElement(high_poly_model, "Mesh")
        high_mesh.set("file", os.path.abspath(high_poly_obj))
        high_mesh.set("scale", "1.0")
        high_mesh.set("ignorePerVertexColor", "true") # Force texture usage over vertex colors
        # We don't specify baseColorTex explicitly here anymore.
        # By not passing it, we force xNormal to read the .mtl file that Trimesh exported alongside the OBJ.
        # This allows multi-material meshes to bake correctly instead of overriding everything with one texture.

        low_poly_model = ET.SubElement(root, "LowPolyModel")
        low_mesh = ET.SubElement(low_poly_model, "Mesh")
        low_mesh.set("file", os.path.abspath(temp_unwrapped_obj))
        low_mesh.set("scale", "1.0")

        generation = ET.SubElement(root, "Generation")
        generation.set("bBakeBaseColor", "true") # Bake Albedo/Diffuse
        generation.set("bBakeNormals", "false")
        generation.set("bBakeAO", "false")
        generation.set("width", str(max_res))
        generation.set("height", str(max_res))
        generation.set("edgePadding", "8") # Prevent bleeding/tearing
        generation.set("output", os.path.abspath(baked_tex_png))
        # Ensure antialiasing is turned on for high quality
        generation.set("aa", "4")

        # Write XML
        tree = ET.ElementTree(root)
        tree.write(xnormal_xml_path)

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

        if not os.path.exists(baked_tex_png):
            print("❌ xNormal failed to generate the baked texture. No output file found.")
            return False

        print(f"✅ xNormal bake complete: {baked_tex_png}")

    except Exception as e:
        print(f"❌ Error during xNormal setup/baking: {e}")
        return False

    # 3. Assemble final GLB
    print(f"🔹 Assembling final GLB to {output_glb}...")
    try:
        from PIL import Image
        # Load the baked texture
        baked_image = Image.open(baked_tex_png)

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
        if os.path.exists(baked_tex_png): os.remove(baked_tex_png)

        return True

    except Exception as e:
        print(f"❌ Error assembling GLB: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UV Unwrap and Bake Textures (xNormal)")
    parser.add_argument("--high_obj", required=True, help="High poly OBJ file")
    parser.add_argument("--low_raw", required=True, help="Low poly raw OBJ file from Instant Meshes")
    parser.add_argument("--output_glb", required=True, help="Output GLB file")
    parser.add_argument("--max_res", type=int, default=1024, help="Max texture resolution")
    parser.add_argument("--xnormal_exe", required=True, help="Path to xNormal executable")

    args = parser.parse_args()
    unwrap_and_bake(args.high_obj, args.low_raw, args.output_glb, args.max_res, args.xnormal_exe)
