import sys
import unittest
from unittest.mock import MagicMock

# Mock bpy and bmesh before importing the module under test
mock_bpy = MagicMock()
sys.modules['bpy'] = mock_bpy

mock_bmesh = MagicMock()
sys.modules['bmesh'] = mock_bmesh

import scripts.blender_worker as worker

class TestTextureResizeEfficiency(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_bpy.reset_mock()
        mock_bmesh.reset_mock()

        # Setup mock images
        self.images = []
        for i in range(110):
            img = MagicMock()
            img.name = f"Image_{i}"
            img.size = [2048, 2048] # All large
            self.images.append(img)

        # 10 Used images (indices 0-9)
        self.used_images = self.images[:10]
        # 100 Unused images (indices 10-109)
        self.unused_images = self.images[10:]

        # Mock bpy.data.images iteration
        mock_bpy.data.images = self.images

        # Setup Active Object with Materials
        self.active_obj = MagicMock()
        self.active_obj.name = "ActiveObject"
        # Mock data attribute
        self.active_obj.data = MagicMock()

        # Create materials using the used images
        self.materials = []
        for img in self.used_images:
            mat = MagicMock()
            mat.use_nodes = True
            node_tree = MagicMock()

            # Create a shader node with the image
            tex_node = MagicMock()
            tex_node.type = 'TEX_IMAGE'
            tex_node.image = img

            # Other random node
            other_node = MagicMock()
            other_node.type = 'BSDF_PRINCIPLED'

            node_tree.nodes = [tex_node, other_node]
            mat.node_tree = node_tree
            self.materials.append(mat)

        # Assign materials to object via material_slots
        # Optimized code iterates obj.material_slots
        self.active_obj.material_slots = []
        for mat in self.materials:
            slot = MagicMock()
            slot.material = mat
            self.active_obj.material_slots.append(slot)

    def test_original_resize_behavior_fallback(self):
        """
        Verify that calling resize_textures WITHOUT objects (fallback)
        still resizes ALL images (backward compatibility).
        """
        max_res = 1024

        worker.resize_textures(max_res)

        # Check that ALL images were resized
        resize_count = 0
        for img in self.images:
            if img.scale.called:
                resize_count += 1
                img.scale.assert_called_with(max_res, max_res)

        print(f"\n[Fallback] Resized {resize_count} images (expected 110)")
        self.assertEqual(resize_count, 110, "Fallback should resize all images")

    def test_optimized_resize_behavior(self):
        """
        Verify that calling resize_textures WITH objects
        only resizes used images.
        """
        max_res = 1024

        # Call with the active object
        worker.resize_textures(max_res, objects=[self.active_obj])

        # Check resized images
        resized_used = 0
        resized_unused = 0

        for img in self.used_images:
            if img.scale.called:
                resized_used += 1
                img.scale.assert_called_with(max_res, max_res)

        for img in self.unused_images:
            if img.scale.called:
                resized_unused += 1

        print(f"\n[Optimized] Resized Used: {resized_used}/10, Unused: {resized_unused}/100")

        self.assertEqual(resized_used, 10, "Should resize all used images")
        self.assertEqual(resized_unused, 0, "Should NOT resize unused images")

    def test_optimized_resize_nested_node_groups(self):
        """
        Verify that images inside node groups are also resized.
        """
        max_res = 1024

        # Create a nested material structure
        mat = MagicMock()
        mat.use_nodes = True

        # Top level tree
        top_tree = MagicMock()

        # Group node
        group_node = MagicMock()
        group_node.type = 'GROUP'
        group_node.node_tree = MagicMock()

        # Node inside group
        inner_tex_node = MagicMock()
        inner_tex_node.type = 'TEX_IMAGE'
        inner_tex_node.image = self.unused_images[0] # Use one of the unused images for this test

        group_node.node_tree.nodes = [inner_tex_node]
        top_tree.nodes = [group_node]
        mat.node_tree = top_tree

        # Assign to active object via material_slots
        slot = MagicMock()
        slot.material = mat
        self.active_obj.material_slots = [slot]

        # Call resize
        worker.resize_textures(max_res, objects=[self.active_obj])

        # Check if the image inside group was resized
        self.unused_images[0].scale.assert_called_with(max_res, max_res)

if __name__ == '__main__':
    unittest.main()
