import sys
import unittest
import time
from unittest.mock import MagicMock, patch

# Mock bpy and bmesh before importing the worker
mock_bpy = MagicMock()
mock_bmesh = MagicMock()

sys.modules['bpy'] = mock_bpy
sys.modules['bmesh'] = mock_bmesh

import scripts.blender_worker as worker

# Create a deeply nested node tree structure
def create_nested_node_tree(depth, branching_factor, image_prob=0.5):
    mock_tree = MagicMock()
    mock_tree.nodes = []

    # Add some images
    for i in range(branching_factor):
        if i % 2 == 0:
            mock_node = MagicMock()
            mock_node.type = 'TEX_IMAGE'
            mock_node.image = MagicMock()
            mock_node.image.name = f"Image_{depth}_{i}"
            mock_tree.nodes.append(mock_node)

    # Add groups (recursion)
    if depth > 0:
        for i in range(branching_factor):
            mock_node = MagicMock()
            mock_node.type = 'GROUP'
            mock_node.node_tree = create_nested_node_tree(depth - 1, branching_factor)
            mock_tree.nodes.append(mock_node)

    return mock_tree

def run_benchmark():
    print("Running baseline benchmark...")
    # Create a complex node tree (depth 8, branching 4 = lots of nodes)
    # This might take a bit to generate the mock tree
    tree = create_nested_node_tree(6, 4)

    start_time = time.time()
    for _ in range(100):
        images = worker.get_images_from_node_tree(tree)
    end_time = time.time()

    elapsed = end_time - start_time
    print(f"Time taken for 100 iterations: {elapsed:.4f} seconds")
    print(f"Found {len(images)} unique images")
    return elapsed

if __name__ == '__main__':
    run_benchmark()
