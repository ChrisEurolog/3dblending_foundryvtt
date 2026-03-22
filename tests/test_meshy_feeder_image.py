import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Mock dependencies to allow importing scripts.meshy_feeder without real dependencies
sys.modules['requests'] = MagicMock()
sys.modules['trimesh'] = MagicMock()
sys.modules['xatlas'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['bpy'] = MagicMock()
sys.modules['bmesh'] = MagicMock()
sys.modules['addon_utils'] = MagicMock()
sys.modules['PIL'] = MagicMock()

# Instead of importing main_pipeline, let's mock it in sys.modules
mock_pipeline = MagicMock()
mock_pipeline.get_app_paths.return_value = MagicMock(base='/fake/base', scripts='/fake/scripts')
mock_pipeline.load_config.return_value = {'meshy_api_key': 'fake_key'}
mock_pipeline.resolve_path.return_value = '/fake/export'
sys.modules['scripts.main_pipeline'] = mock_pipeline

import scripts.meshy_feeder as feeder

class TestMeshyFeederImage(unittest.TestCase):
    @patch('os.path.getsize')
    def test_get_base64_image_png(self, mock_getsize):
        mock_getsize.return_value = 100
        m = mock_open(read_data=b"fake_image_data")
        with patch('builtins.open', m):
            result = feeder.get_base64_image("test_image.png")
            # b"fake_image_data" encoded is 'ZmFrZV9pbWFnZV9kYXRh'
            self.assertEqual(result, "data:image/png;base64,ZmFrZV9pbWFnZV9kYXRh")

    @patch('os.path.getsize')
    def test_get_base64_image_jpg(self, mock_getsize):
        mock_getsize.return_value = 100
        m = mock_open(read_data=b"fake_image_data")
        with patch('builtins.open', m):
            result = feeder.get_base64_image("test_image.jpg")
            self.assertEqual(result, "data:image/jpeg;base64,ZmFrZV9pbWFnZV9kYXRh")

    @patch('os.path.getsize')
    def test_get_base64_image_jpeg(self, mock_getsize):
        mock_getsize.return_value = 100
        m = mock_open(read_data=b"fake_image_data")
        with patch('builtins.open', m):
            result = feeder.get_base64_image("test_image.jpeg")
            self.assertEqual(result, "data:image/jpeg;base64,ZmFrZV9pbWFnZV9kYXRh")

    @patch('os.path.getsize')
    def test_get_base64_image_case_insensitive(self, mock_getsize):
        mock_getsize.return_value = 100
        m = mock_open(read_data=b"fake_image_data")
        with patch('builtins.open', m):
            result = feeder.get_base64_image("test_image.PNG")
            self.assertEqual(result, "data:image/png;base64,ZmFrZV9pbWFnZV9kYXRh")

if __name__ == '__main__':
    unittest.main()
