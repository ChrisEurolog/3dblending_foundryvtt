import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock bpy, bmesh and addon_utils before importing the worker
mock_bpy = MagicMock()
mock_bmesh = MagicMock()
mock_addon_utils = MagicMock()

sys.modules['bpy'] = mock_bpy
sys.modules['bmesh'] = mock_bmesh
sys.modules['addon_utils'] = mock_addon_utils

# Now we can import the worker and the benchmark functions
import scripts.blender_worker as worker
from benchmark_node_tree import create_nested_node_tree

class TestBenchmarkNodeTree(unittest.TestCase):

    def test_create_nested_node_tree_depth_0(self):
        """Verify that a tree with depth 0 and branching factor 4 creates exactly 2 TEX_IMAGE nodes."""
        # branching_factor=4, indices i=0,1,2,3
        # i%2==0 for 0, 2 -> 2 TEX_IMAGE nodes
        # depth=0 -> no GROUP nodes
        tree = create_nested_node_tree(0, 4)
        self.assertEqual(len(tree.nodes), 2)
        self.assertTrue(all(node.type == 'TEX_IMAGE' for node in tree.nodes))

    def test_create_nested_node_tree_depth_1(self):
        """Verify that a tree with depth 1 and branching factor 2 creates 1 TEX_IMAGE and 2 GROUP nodes."""
        # depth=1, branching_factor=2
        # TEX_IMAGE: i=0 (1 node)
        # GROUP: i=0, 1 (2 nodes)
        # Total: 3 nodes at top level
        tree = create_nested_node_tree(1, 2)
        self.assertEqual(len(tree.nodes), 3)

        tex_images = [n for n in tree.nodes if n.type == 'TEX_IMAGE']
        groups = [n for n in tree.nodes if n.type == 'GROUP']

        self.assertEqual(len(tex_images), 1)
        self.assertEqual(len(groups), 2)

    def test_get_images_from_node_tree_integration(self):
        """Verify that worker.get_images_from_node_tree correctly identifies images in a nested tree."""
        # depth=1, branching_factor=2
        # Top level: 1 image (i=0)
        # Group 1 (i=0): depth 0, branching 2 -> 1 image (i=0)
        # Group 2 (i=1): depth 0, branching 2 -> 1 image (i=0)
        # Total: 3 images
        tree = create_nested_node_tree(1, 2)
        images = worker.get_images_from_node_tree(tree)
        self.assertEqual(len(images), 3)

        # Verify they are unique mock objects (sets handle this by object identity)
        self.assertIsInstance(images, set)
        for img in images:
            self.assertTrue(hasattr(img, 'name'))

    def test_get_images_from_node_tree_empty(self):
        """Verify that worker.get_images_from_node_tree handles None or empty input."""
        images = worker.get_images_from_node_tree(None)
        self.assertEqual(len(images), 0)
        self.assertIsInstance(images, set)

if __name__ == '__main__':
    unittest.main()
