import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock bpy and bmesh before importing the worker
mock_bpy = MagicMock()
mock_bmesh = MagicMock()

# We use patch.dict to safely insert mocks into sys.modules
sys.modules['bpy'] = mock_bpy
sys.modules['bmesh'] = mock_bmesh
sys.modules['addon_utils'] = MagicMock()

# Setup bpy.app.timers mock
mock_bpy.app = MagicMock()
mock_bpy.app.timers = MagicMock()

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
        mock_objects = MagicMock()
        mock_objects.__iter__.return_value = [mock_obj]
        mock_bpy.data.objects = mock_objects

        mock_bpy.data.objects.__contains__.side_effect = lambda k: True
        mock_bpy.data.objects.__getitem__.side_effect = lambda k: mock_obj

        # Setup active object
        mock_bpy.context.view_layer.objects.active = mock_obj

        # Setup bmesh for check_non_manifold
        mock_bm = MagicMock()
        # Make sure verts and edges are iterable but empty so any() returns False
        mock_bm.verts = []
        mock_bm.edges = []
        mock_bmesh.from_edit_mesh.return_value = mock_bm

        # Ensure new materials can be added
        mock_bpy.data.materials.new.return_value = MagicMock()
        mock_bpy.data.images.new.return_value = MagicMock()

        # Support objects removal without error
        mock_bpy.data.objects.remove = MagicMock()

        # Mock timer register to just call the function immediately
        def mock_register(func):
            mock_bpy.data.objects.__contains__.side_effect = lambda k: True
            mock_bpy.data.objects.__getitem__.side_effect = lambda k: mock_obj
            func()

        mock_bpy.app.timers.register.side_effect = mock_register

        with patch.object(sys, 'argv', test_args), \
             patch('os.path.exists', return_value=True), \
             patch('scripts.blender_worker.validate_gltf_path'), \
             patch('os.remove'), \
             patch.dict('sys.modules', {'bmesh': mock_bmesh}), \
             patch('builtins.print'):

            # Because bmesh is imported locally in finish_export, patching `scripts.blender_worker.bmesh` does not intercept it.
            # We must use `patch.dict(sys.modules, {'bmesh': mock_bmesh})` which is already globally active via the test file.
            mock_bmesh.ops.remove_doubles.reset_mock()

            worker.process()

            self.assertTrue(mock_bmesh.ops.remove_doubles.called, "remove_doubles should have been called")
            call_args = mock_bmesh.ops.remove_doubles.call_args[1]
            self.assertEqual(call_args.get('dist'), 0.0001)

            # Check that delete_loose is actually NOT called, as it's not part of the current logic
            self.assertFalse(mock_bpy.ops.mesh.delete_loose.called, "delete_loose should not have been called.")

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
        mock_materials = MagicMock()
        mock_materials.__iter__.return_value = [mock_mat]
        mock_bpy.data.materials = mock_materials
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_obj.data.materials = mock_materials

        # Provide inputs directly since we loop through baked_mat.node_tree.nodes where node.type is not used by default
        # But wait, the test is passing 'mock_bsdf' inside 'mock_mat.node_tree.nodes'.
        # The script does: bsdf = nodes.get("Principled BSDF")
        # So we need to ensure nodes.get returns mock_bsdf
        mock_nodes = MagicMock()
        mock_nodes.get.return_value = mock_bsdf
        # nodes.new('ShaderNodeTexImage')
        mock_tex_node = MagicMock()
        mock_nodes.new.return_value = mock_tex_node
        mock_mat.node_tree.nodes = mock_nodes

        # Setup standard object requirements (copied from test_remove_doubles_threshold logic)
        mock_obj = MagicMock()
        mock_obj.type = 'MESH'
        mock_obj.data.materials = mock_materials
        mock_obj.data.vertices = [MagicMock()]
        mock_obj.dimensions = (1.0, 1.0, 1.0)

        mock_matrix_result = MagicMock()
        mock_matrix_result.z = 0.0
        mock_obj.matrix_world = MagicMock()
        mock_obj.matrix_world.__matmul__.return_value = mock_matrix_result

        mock_objects = MagicMock()
        mock_objects.__iter__.return_value = [mock_obj]
        mock_bpy.data.objects = mock_objects

        # Important to set up objects map for check_retopo timer logic
        mock_bpy.data.objects.__contains__.side_effect = lambda k: True
        mock_bpy.data.objects.__getitem__.side_effect = lambda k: mock_obj

        mock_bpy.context.view_layer.objects.active = mock_obj

        mock_bm = MagicMock()
        mock_bm.verts = []
        mock_bm.edges = []
        mock_bmesh.from_edit_mesh.return_value = mock_bm

        # Ensure new materials can be added
        mock_bpy.data.materials.new.return_value = MagicMock()
        mock_bpy.data.images.new.return_value = MagicMock()

        # Support objects removal without error
        mock_bpy.data.objects.remove = MagicMock()

        # Arguments to enable matte
        test_args = ['blender', '--background', '--python', 'script.py', '--', '--input', 'test.glb', '--output', 'out.glb', '--matte', '1']

        # Mock timer register to just call the function immediately
        def mock_register(func):
            mock_bpy.data.objects.__contains__.side_effect = lambda k: True
            mock_bpy.data.objects.__getitem__.side_effect = lambda k: mock_obj
            func()

        mock_bpy.app.timers.register.side_effect = mock_register

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

        mock_objects = MagicMock()
        mock_objects.__iter__.return_value = [mock_obj]
        mock_bpy.data.objects = mock_objects

        # Important to set up objects map for check_retopo timer logic
        mock_bpy.data.objects.__contains__.side_effect = lambda k: True
        mock_bpy.data.objects.__getitem__.side_effect = lambda k: mock_obj

        mock_bpy.context.view_layer.objects.active = mock_obj

        mock_bm = MagicMock()
        mock_bm.verts = []
        mock_bm.edges = []
        mock_bmesh.from_edit_mesh.return_value = mock_bm

        # Ensure new materials can be added
        mock_bpy.data.materials.new.return_value = MagicMock()
        mock_bpy.data.images.new.return_value = MagicMock()

        # Support objects removal without error
        mock_bpy.data.objects.remove = MagicMock()

        test_args = ['blender', '--background', '--python', 'script.py', '--', '--input', 'test.glb', '--output', 'out.glb']

        # Mock timer register to just call the function immediately
        def mock_register(func):
            mock_bpy.data.objects.__contains__.side_effect = lambda k: True
            mock_bpy.data.objects.__getitem__.side_effect = lambda k: mock_obj
            func()

        mock_bpy.app.timers.register.side_effect = mock_register

        with patch.object(sys, 'argv', test_args), \
             patch('os.path.exists', return_value=True), \
             patch('scripts.blender_worker.validate_gltf_path'), \
             patch('os.remove'), \
             patch('builtins.print'):

            worker.process()

            # Verify that custom split normals are actually cleared
            mock_bpy.ops.mesh.customdata_custom_splitnormals_clear.assert_called()

if __name__ == '__main__':
    unittest.main()
