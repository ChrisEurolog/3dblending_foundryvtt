import unittest
import os
import trimesh
from PIL import Image
from unittest.mock import patch, MagicMock

class TestBake(unittest.TestCase):
    @patch('scripts.bake_textures.subprocess.run')
    def test_unwrap_and_bake(self, mock_run):
        # Mock xNormal subprocess
        mock_run.return_value = MagicMock(returncode=0, stdout="Mock xNormal success", stderr="")

        # Create mock inputs
        high_obj = "mock_high.obj"
        high_tex = "mock_tex.png"
        low_raw = "mock_low_raw.obj"
        output_glb = "mock_output.glb"

        # Box needs UVs for PyMeshLab/xNormal to transfer texture
        box1 = trimesh.creation.box()
        box1.visual = trimesh.visual.TextureVisuals(uv=box1.vertices[:, :2]) # Mock UVs
        box1.export(high_obj)
        box2 = trimesh.creation.box()
        box2.export(low_raw)

        im = Image.new('RGB', (16, 16), color = 'red')
        im.save(high_tex)

        # Mock the baked texture creation that xNormal would have done
        def side_effect(*args, **kwargs):
            xml_path = args[0][1]
            baked_png = xml_path.replace("_xnormal.xml", "_baked.png")
            im.save(baked_png)
            return MagicMock(returncode=0, stdout="Mock xNormal success", stderr="")
        mock_run.side_effect = side_effect

        # Test script execution via imported function
        from scripts.bake_textures import unwrap_and_bake
        # Mock xnormal exe path to pass exists check
        import tempfile
        with tempfile.NamedTemporaryFile() as fake_exe:
            res = unwrap_and_bake(high_obj, low_raw, high_tex, output_glb, 1024, fake_exe.name)

        self.assertTrue(res)
        self.assertTrue(os.path.exists(output_glb))

        # Cleanup
        os.remove(high_obj)
        os.remove(low_raw)
        os.remove(high_tex)
        if os.path.exists(output_glb):
            os.remove(output_glb)
