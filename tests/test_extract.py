import unittest
import os
import sys
import trimesh
from PIL import Image

class TestExtract(unittest.TestCase):
    def test_extract_mesh_and_texture(self):
        # Create a tiny mock GLB to test with
        mesh = trimesh.creation.box()
        # Add a simple texture material
        im = Image.new('RGB', (16, 16), color = 'red')
        mat = trimesh.visual.material.PBRMaterial(baseColorTexture=im)
        mesh.visual = trimesh.visual.TextureVisuals(material=mat, image=im)

        test_in = "test_box.glb"
        test_obj = "out_box.obj"
        mesh.export(test_in)

        os.system(f'"{sys.executable}" scripts/extract_glb.py --input {test_in} --output_obj {test_obj}')

        self.assertTrue(os.path.exists(test_obj))
        # Trimesh automatically creates the associated .mtl and material_0.png
        # In this specific test context with force=scene, Trimesh outputs material.mtl
        self.assertTrue(os.path.exists("material.mtl"))
        self.assertTrue(os.path.exists("material_0.png"))

        # Cleanup
        os.remove(test_in)
        os.remove(test_obj)
        if os.path.exists("material.mtl"):
            os.remove("material.mtl")
        if os.path.exists("material_0.png"):
            os.remove("material_0.png")
