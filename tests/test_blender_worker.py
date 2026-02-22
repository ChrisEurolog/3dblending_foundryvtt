import sys
import unittest
from unittest.mock import MagicMock, patch
import importlib

class TestBlenderWorker(unittest.TestCase):
    def setUp(self):
        # We need to mock bpy and bmesh before importing blender_worker
        self.mock_bpy = MagicMock()
        self.mock_bmesh = MagicMock()

        # Patch sys.modules to include our mocks
        self.modules_patcher = patch.dict(sys.modules, {
            'bpy': self.mock_bpy,
            'bmesh': self.mock_bmesh
        })
        self.modules_patcher.start()

        # Import or reload the module to ensure it picks up the mocked modules
        if 'scripts.blender_worker' in sys.modules:
            import scripts.blender_worker
            importlib.reload(scripts.blender_worker)
        else:
            import scripts.blender_worker
        self.worker = scripts.blender_worker

    def tearDown(self):
        self.modules_patcher.stop()
        # Remove the module from sys.modules to ensure fresh import for other tests if needed
        if 'scripts.blender_worker' in sys.modules:
            del sys.modules['scripts.blender_worker']

    @patch('os.path.exists')
    def test_process_calls_remove_doubles_with_threshold(self, mock_exists):
        mock_exists.return_value = True

        # Setup bpy mock structure
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'

        # Setup vertices for bottom_z calculation
        mock_vertex = MagicMock()
        mock_result = MagicMock()
        mock_result.z = 0.0

        # When (matrix @ vector) happens, return mock_result
        mock_obj.matrix_world.__matmul__.return_value = mock_result

        # Configure data.vertices list
        mock_obj.data.vertices = [mock_vertex]

        # Configure dimensions
        mock_obj.dimensions = [1.0, 1.0, 1.0]

        # Ensure bpy.data.objects returns this object
        self.mock_bpy.data.objects = [mock_obj]

        # Run with patched sys.argv
        with patch('sys.argv', ['script_name', '--', '--input', 'test.glb', '--output', 'out.glb']):
             self.worker.process()

        # Verify remove_doubles call
        # The threshold is currently 0.002
        self.mock_bpy.ops.mesh.remove_doubles.assert_called_with(threshold=0.002)

if __name__ == '__main__':
    unittest.main()
