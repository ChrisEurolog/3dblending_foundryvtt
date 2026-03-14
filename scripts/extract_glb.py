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
        return False, None

    # We need to manually extract the texture image to pass directly to xNormal
    # because xNormal batch mode does not reliably parse .mtl files for diffuse baking.
    tex_path = None
    for name, geom in scene.geometry.items():
        if hasattr(geom.visual, 'material'):
            mat = geom.visual.material
            # Depending on Trimesh version and material type (PBRMaterial vs SimpleMaterial)
            image = None
            if hasattr(mat, 'baseColorTexture') and mat.baseColorTexture is not None:
                image = mat.baseColorTexture
            elif hasattr(mat, 'image') and mat.image is not None:
                image = mat.image

            if image:
                tex_path = output_obj.replace('.obj', '_diffuse.png')
                image.save(tex_path)
                print(f"✅ Extracted diffuse texture to {tex_path}")
                break # Just take the first valid texture found for now

    print("🔹 Exporting high-poly geometry to OBJ...")
    mesh = scene.dump(concatenate=True)

    # We still export the obj, but we will explicitly pass tex_path to xNormal later
    mesh.export(output_obj, include_texture=True)

    return True, tex_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract OBJ and materials from GLB")
    parser.add_argument("--input", required=True, help="Input GLB file path")
    parser.add_argument("--output_obj", required=True, help="Output OBJ file path")
    args = parser.parse_args()

    extract_glb(args.input, args.output_obj)
