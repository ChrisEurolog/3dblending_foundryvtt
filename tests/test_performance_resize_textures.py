import sys
import unittest
from unittest.mock import MagicMock, patch
import time

# Mock bpy and bmesh
mock_bpy = MagicMock()
mock_bmesh = MagicMock()
sys.modules['bpy'] = mock_bpy
sys.modules['bmesh'] = mock_bmesh

import scripts.blender_worker as worker

class TestPerformanceResizeTextures(unittest.TestCase):
    def test_redundant_material_traversal(self):
        # Setup many objects sharing the same material
        num_objects = 1000
        mock_mat = MagicMock()
        mock_mat.use_nodes = True
        mock_mat.node_tree.nodes = []
        # Add some nodes to the material
        for i in range(10):
            node = MagicMock()
            node.type = 'TEX_IMAGE'
            node.image = MagicMock()
            node.image.name = f"img_{i}"
            node.image.size = [512, 512] # Ensure comparison works
            mock_mat.node_tree.nodes.append(node)

        mock_objects = []
        for i in range(num_objects):
            obj = MagicMock()
            slot = MagicMock()
            slot.material = mock_mat
            obj.material_slots = [slot]
            mock_objects.append(obj)

        # We want to measure how many times get_images_from_node_tree is called

        with patch('scripts.blender_worker.get_images_from_node_tree', side_effect=worker.get_images_from_node_tree) as mock_get_images, \
             patch('builtins.print'): # Suppress print output
            start_time = time.time()
            worker.resize_textures(1024, objects=mock_objects)
            end_time = time.time()

            call_count = mock_get_images.call_count

            # Assert that it's only called once for the shared material
            self.assertEqual(call_count, 1)

if __name__ == '__main__':
    unittest.main()
