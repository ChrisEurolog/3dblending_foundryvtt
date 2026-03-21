import sys
import unittest
import os
from unittest.mock import MagicMock, patch

mock_bpy = MagicMock()
sys.modules['bpy'] = mock_bpy

mock_bmesh = MagicMock()
sys.modules['bmesh'] = mock_bmesh

import scripts.blender_unwrap_bake as be

class TestBlenderUnwrapBake(unittest.TestCase):
    def setUp(self):
        mock_bpy.reset_mock()

    @patch('sys.exit')
    @patch('builtins.print')
    @patch('os.path.exists')
    @patch('xml.etree.ElementTree.ElementTree.write')
    @patch('subprocess.run')
    @patch('time.time', side_effect=[0, 10, 20])
    @patch('time.sleep')
    @patch('os.path.getsize', return_value=1024)
    @patch('os.remove')
    def test_normals_make_consistent_called(self, mock_remove, mock_getsize, mock_sleep, mock_time, mock_subprocess, mock_write, mock_exists, mock_print, mock_exit):
        mock_exists.return_value = True

        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_bpy.data.objects = [mock_obj]
        mock_bpy.context.view_layer.objects.active = mock_obj

        test_args = ['blender', '--background', '--python', 'blender_unwrap_bake.py', '--', 'high.obj', 'low.obj', 'high_tex.png', 'out.glb', 'xnormal.exe']

        with patch.object(sys, 'argv', test_args):
            be.process()

        mock_bpy.ops.mesh.normals_make_consistent.assert_called_with(inside=False)

if __name__ == '__main__':
    unittest.main()
