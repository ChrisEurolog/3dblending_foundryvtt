import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock bpy before importing blender_unwrap_bake
mock_bpy = MagicMock()
sys.modules['bpy'] = mock_bpy

import scripts.blender_unwrap_bake as be

class TestBlenderUnwrapBake(unittest.TestCase):
    def setUp(self):
        mock_bpy.reset_mock()
        mock_bpy.data.objects = []

    @patch('sys.exit')
    @patch('builtins.print')
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_normals_make_consistent_called(self, mock_run, mock_exists, mock_print, mock_exit):
        mock_exists.return_value = True

        # Setup mock objects
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_obj.data.vertices = [1] * 100
        mock_bpy.data.objects = [mock_obj]

        mock_bpy.context.view_layer.objects.active = mock_obj

        test_args = ['blender', '--background', '--python', 'blender_unwrap_bake.py', '--', 'high.obj', 'low.obj', 'tex.png', 'out.glb', 'xnormal.exe']

        mock_bpy.ops.wm.obj_export = MagicMock()
        mock_bpy.ops.wm.quit_blender = MagicMock()
        mock_bpy.ops.export_scene.gltf = MagicMock()

        with patch.object(sys, 'argv', test_args):
            with patch.dict('sys.modules', {'bmesh': MagicMock()}):
                with patch('os.remove'):
                    be.process()

        mock_bpy.ops.mesh.normals_make_consistent.assert_called_with(inside=False)
        mock_bpy.ops.mesh.customdata_custom_splitnormals_clear.assert_called()

if __name__ == '__main__':
    unittest.main()
