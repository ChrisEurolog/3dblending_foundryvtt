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
    def test_normals_make_consistent_called(self, mock_exists, mock_print, mock_exit):
        mock_exists.return_value = True

        # Setup mock objects
        # We need two mock objects to simulate high and low poly meshes
        # High poly is imported first
        mock_high_obj = MagicMock()
        mock_high_obj.type = 'MESH'
        mock_high_obj.name = "HighPoly"
        mock_high_obj.data.vertices = [MagicMock(co=MagicMock(x=0, y=0, z=0))] * 100

        # Low poly is imported second
        mock_low_obj = MagicMock()
        mock_low_obj.type = 'MESH'
        mock_low_obj.name = "LowPoly"
        mock_low_obj.data.vertices = [MagicMock(co=MagicMock(x=0, y=0, z=0))] * 100
        mock_low_obj.dimensions = [1.0, 1.0, 1.0]
        mock_low_obj.bound_box = [[0,0,0], [1,1,1]]

        # We need to simulate bpy.data.objects changing between imports
        # After high poly import, it has only high poly
        # After low poly import, it has both
        # A simple way without complex side_effect is to just populate both
        # but blender_unwrap_bake uses `obj not in high_poly_objs`.
        # So we can set side_effect for the obj_import to mutate bpy.data.objects
        mock_bpy.data.objects = []

        def mock_obj_import(filepath, **kwargs):
            if "high" in filepath:
                mock_bpy.data.objects.append(mock_high_obj)
            else:
                mock_bpy.data.objects.append(mock_low_obj)

        mock_bpy.ops.wm.obj_import = MagicMock(side_effect=mock_obj_import)

        mock_bpy.context.view_layer.objects.active = mock_low_obj

        test_args = ['blender', '--background', '--python', 'blender_unwrap_bake.py', '--', 'high.obj', 'low.obj', 'tex.png', 'out.glb', '1024', '20000']

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
