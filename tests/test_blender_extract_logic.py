import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock bpy before importing blender_extract
mock_bpy = MagicMock()
sys.modules['bpy'] = mock_bpy

import scripts.blender_extract as be

class TestBlenderExtractLogic(unittest.TestCase):
    def setUp(self):
        mock_bpy.reset_mock()
        mock_bpy.data.objects = []

    @patch('sys.exit')
    @patch('builtins.print')
    @patch('os.path.exists')
    @patch('scripts.blender_extract.validate_gltf_path')
    def test_extract_glb_no_geometry(self, mock_validate, mock_exists, mock_print, mock_exit):
        """
        Test that when no MESH objects are found in the GLB,
        the script prints an error and exits with code 1.
        """
        mock_exists.return_value = True
        mock_validate.return_value = True

        # Simulate sys.argv
        test_args = ['blender', '--background', '--python', 'blender_extract.py', '--', 'input.glb', 'output.obj']

        # mock_exit should raise an exception (like sys.exit does) to prevent continuing to line 122
        mock_exit.side_effect = SystemExit(1)

        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                be.process()
            self.assertEqual(cm.exception.code, 1)

        # Assertions
        mock_print.assert_any_call("❌ No mesh objects found in GLB.")
        mock_exit.assert_called_once_with(1)


    @patch('sys.exit')
    @patch('builtins.print')
    @patch('os.path.exists')
    @patch('scripts.blender_extract.validate_gltf_path')
    def test_normals_make_consistent_called(self, mock_validate, mock_exists, mock_print, mock_exit):
        mock_exists.return_value = True
        mock_validate.return_value = True

        # Setup mock objects
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_obj.data.vertices = [1] * 100
        mock_bpy.data.objects = [mock_obj]

        mock_bpy.context.view_layer.objects.active = mock_obj

        test_args = ['blender', '--background', '--python', 'blender_extract.py', '--', 'input.glb', 'output.obj']

        # We need to stub out the save method so it doesn't crash on mocked images
        mock_bpy.ops.wm.obj_export = MagicMock()
        mock_bpy.ops.wm.quit_blender = MagicMock()

        with patch.object(sys, 'argv', test_args):
            be.process()

        mock_bpy.ops.mesh.normals_make_consistent.assert_called_with(inside=False)

if __name__ == '__main__':
    unittest.main()
