import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock bpy and bmesh before importing the worker
mock_bpy = MagicMock()
mock_bmesh = MagicMock()

# We use patch.dict to safely insert mocks into sys.modules
sys.modules['bpy'] = mock_bpy
sys.modules['bmesh'] = mock_bmesh

import scripts.blender_worker as worker

class TestBlenderWorker(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test if needed
        mock_bpy.reset_mock()
        mock_bmesh.reset_mock()

    def test_missing_input_exits_with_error(self):
        """
        Verifies that the script exits with status code 1 when the input file is missing.
        """
        test_args = ['blender', '--background', '--python', 'script.py', '--', '--input', 'missing.glb', '--output', 'out.glb']

        with patch.object(sys, 'argv', test_args), \
             patch('os.path.exists', return_value=False), \
             patch('sys.exit') as mock_exit, \
             patch('builtins.print') as mock_print, \
             patch('scripts.blender_worker.validate_gltf_path'):

            worker.process()

            # Assert sys.exit was called with 1
            mock_exit.assert_called_with(1)

            # Verify error message
            printed_error = any("Error: Input file" in str(args[0]) for args, _ in mock_print.call_args_list if args)
            self.assertTrue(printed_error, "Error message should be printed")

    def test_remove_doubles_threshold(self):
        """
        Verifies that remove_doubles is called with a threshold of 0.002.
        """
        test_args = ['blender', '--background', '--python', 'script.py', '--', '--input', 'test.glb', '--output', 'out.glb']

        # Setup mocks for mesh objects
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_obj.data.uv_layers = [] # Avoid index error if code checks
        mock_obj.dimensions = (1.0, 1.0, 1.0) # Ensure dimensions are iterable and not empty

        # Setup vertices for bottom_z calculation
        mock_vert = MagicMock()
        mock_vert.co = MagicMock()
        mock_obj.data.vertices = [mock_vert]

        # Mock matrix multiplication result
        # When (mock_obj.matrix_world @ v.co) happens, it returns a mock with .z
        mock_matrix_result = MagicMock()
        mock_matrix_result.z = 0.0
        # Configure __matmul__ on the matrix_world mock
        # We need to ensure matrix_world is a mock that supports matmul
        mock_obj.matrix_world = MagicMock()
        mock_obj.matrix_world.__matmul__.return_value = mock_matrix_result

        # We need at least one mesh object to proceed to the joining step
        mock_bpy.data.objects = [mock_obj]

        # Setup active object
        mock_bpy.context.view_layer.objects.active = mock_obj

        # Setup bmesh for check_non_manifold
        mock_bm = MagicMock()
        # Make sure verts and edges are iterable but empty so any() returns False
        mock_bm.verts = []
        mock_bm.edges = []
        mock_bmesh.from_edit_mesh.return_value = mock_bm

        with patch.object(sys, 'argv', test_args), \
             patch('os.path.exists', return_value=True), \
             patch('scripts.blender_worker.validate_gltf_path'), \
             patch('builtins.print'): # Suppress print output

            worker.process()

            # Assert remove_doubles was called with threshold=0.002
            mock_bpy.ops.mesh.remove_doubles.assert_called_with(threshold=0.002)

if __name__ == '__main__':
    unittest.main()
