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
        Verifies that remove_doubles is called with a threshold of 0.0005 to prevent jagged artifacts from over-merging.
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

            # Assert remove_doubles was called with threshold=0.0005
            mock_bpy.ops.mesh.remove_doubles.assert_called_with(threshold=0.0005)

    def test_mattening_removes_metallic_and_fixes_roughness(self):
        """
        Verifies that the mattening pass:
        1. Sets Metallic default to 0.0
        2. Removes links to Metallic
        3. Sets Roughness default to 0.8
        4. Removes links to Roughness (to ensure matte look)
        """
        # Create a mock material with a Principled BSDF
        mock_mat = MagicMock()
        mock_mat.use_nodes = True

        mock_bsdf = MagicMock()
        mock_bsdf.type = 'BSDF_PRINCIPLED'

        # Setup inputs dict
        mock_metallic_input = MagicMock()
        mock_metallic_input.default_value = 1.0 # Originally metallic
        mock_metallic_input.links = [MagicMock()] # Has a link

        mock_roughness_input = MagicMock()
        mock_roughness_input.default_value = 0.2 # Originally shiny
        mock_roughness_input.links = [MagicMock()] # Has a link

        # Determine inputs based on key access
        def get_input(key):
            if key == 'Metallic':
                return mock_metallic_input
            if key == 'Roughness':
                return mock_roughness_input
            return MagicMock()

        mock_bsdf.inputs.__getitem__.side_effect = get_input
        mock_bsdf.inputs.__contains__.side_effect = lambda key: key in ['Metallic', 'Roughness']

        mock_mat.node_tree.nodes = [mock_bsdf]
        mock_bpy.data.materials = [mock_mat]

        # Setup standard object requirements (copied from test_remove_doubles_threshold logic)
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_obj.data.vertices = [MagicMock()]
        mock_obj.dimensions = (1.0, 1.0, 1.0)

        mock_matrix_result = MagicMock()
        mock_matrix_result.z = 0.0
        mock_obj.matrix_world = MagicMock()
        mock_obj.matrix_world.__matmul__.return_value = mock_matrix_result

        mock_bpy.data.objects = [mock_obj]
        mock_bpy.context.view_layer.objects.active = mock_obj

        mock_bm = MagicMock()
        mock_bm.verts = []
        mock_bm.edges = []
        mock_bmesh.from_edit_mesh.return_value = mock_bm

        # Arguments to enable matte
        test_args = ['blender', '--background', '--python', 'script.py', '--', '--input', 'test.glb', '--output', 'out.glb', '--matte', '1']

        with patch.object(sys, 'argv', test_args), \
             patch('os.path.exists', return_value=True), \
             patch('scripts.blender_worker.validate_gltf_path'), \
             patch('builtins.print'):

            worker.process()

            # Assertions
            self.assertEqual(mock_metallic_input.default_value, 0.0)
            self.assertTrue(mock_mat.node_tree.links.remove.called)
            self.assertEqual(mock_roughness_input.default_value, 0.8)

    def test_clears_split_normals(self):
        """
        Verifies that custom split normals are cleared before smoothing
        to fix jagged edges on imported geometry.
        """
        # Setup standard object requirements
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_obj.data.vertices = [MagicMock()]
        mock_obj.dimensions = (1.0, 1.0, 1.0)

        mock_matrix_result = MagicMock()
        mock_matrix_result.z = 0.0
        mock_obj.matrix_world = MagicMock()
        mock_obj.matrix_world.__matmul__.return_value = mock_matrix_result

        mock_bpy.data.objects = [mock_obj]
        mock_bpy.context.view_layer.objects.active = mock_obj

        mock_bm = MagicMock()
        mock_bm.verts = []
        mock_bm.edges = []
        mock_bmesh.from_edit_mesh.return_value = mock_bm

        test_args = ['blender', '--background', '--python', 'script.py', '--', '--input', 'test.glb', '--output', 'out.glb']

        with patch.object(sys, 'argv', test_args), \
             patch('os.path.exists', return_value=True), \
             patch('scripts.blender_worker.validate_gltf_path'), \
             patch('builtins.print'):

            worker.process()

            # Assert customdata_custom_splitnormals_clear was called
            mock_bpy.ops.mesh.customdata_custom_splitnormals_clear.assert_called()

if __name__ == '__main__':
    unittest.main()
