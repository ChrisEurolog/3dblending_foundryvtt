import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock bpy and bmesh modules before importing the script
sys.modules['bpy'] = MagicMock()
sys.modules['bmesh'] = MagicMock()

import scripts.blender_worker as bw

class TestBlenderWorker(unittest.TestCase):
    def setUp(self):
        # Reset mocks before each test
        sys.modules['bpy'].reset_mock()
        self.mock_bpy = sys.modules['bpy']

    def test_resize_textures_square(self):
        # Case 1: Square image larger than max_res
        img = MagicMock()
        img.size = [2048, 2048]
        img.name = "Square"
        self.mock_bpy.data.images = [img]

        bw.resize_textures(1024)

        img.scale.assert_called_with(1024, 1024)

    def test_resize_textures_wide(self):
        # Case 2: Wide image larger than max_res
        img = MagicMock()
        img.size = [2048, 1024]
        img.name = "Wide"
        self.mock_bpy.data.images = [img]

        bw.resize_textures(1024)

        # Should be scaled to 1024 width, height scaled proportionally
        # 1024 / 2048 = 0.5 -> height = 1024 * 0.5 = 512
        img.scale.assert_called_with(1024, 512)

    def test_resize_textures_tall(self):
        # Case 3: Tall image larger than max_res
        img = MagicMock()
        img.size = [1024, 2048]
        img.name = "Tall"
        self.mock_bpy.data.images = [img]

        bw.resize_textures(1024)

        # Should be scaled to 1024 height, width scaled proportionally
        # 1024 / 2048 = 0.5 -> width = 1024 * 0.5 = 512
        img.scale.assert_called_with(512, 1024)

    def test_resize_textures_small(self):
        # Case 4: Image smaller than max_res should not be resized
        img = MagicMock()
        img.size = [512, 512]
        img.name = "Small"
        self.mock_bpy.data.images = [img]

        bw.resize_textures(1024)

        img.scale.assert_not_called()

    def test_resize_textures_mixed_small(self):
        # Case 5: One dimension larger, one smaller
        img = MagicMock()
        img.size = [1500, 500]
        img.name = "Mixed"
        self.mock_bpy.data.images = [img]

        bw.resize_textures(1024)

        # Max dim is 1500. Scale factor = 1024 / 1500 = 0.68266...
        # Width = 1500 * (1024/1500) = 1024
        # Height = 500 * (1024/1500) = 341.33 -> 341
        img.scale.assert_called_with(1024, 341)

if __name__ == '__main__':
    unittest.main()
