import trimesh
import os
import argparse
from PIL import Image
import io

def extract_glb(input_glb, output_obj):
    print(f"🔹 Extracting geometry and textures from: {input_glb}")
    scene = trimesh.load(input_glb, force='scene')

    # Check if there's any geometry
    if not scene.geometry:
        print("❌ Error: No geometry found in the GLB file.")
        return False

    # Export high-poly geometry and its MTL/Textures
    # By saving to OBJ with Trimesh, it automatically dumps the .mtl and any associated texture files
    # into the same directory as output_obj. This correctly preserves multi-material setups
    # and allows xNormal to read the materials directly via the .obj file.
    print("🔹 Exporting high-poly geometry and materials to OBJ...")
    mesh = scene.dump(concatenate=True)

    # Ensure export includes materials
    # We pass include_normals=True and include_texture=True to ensure xNormal gets all data
    # We don't manually extract a single texture anymore, xNormal will read the MTL
    mesh.export(output_obj, include_texture=True)

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract OBJ and materials from GLB")
    parser.add_argument("--input", required=True, help="Input GLB file path")
    parser.add_argument("--output_obj", required=True, help="Output OBJ file path")
    args = parser.parse_args()

    extract_glb(args.input, args.output_obj)
