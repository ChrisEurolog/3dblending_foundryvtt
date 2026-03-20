import unittest
from unittest.mock import patch, MagicMock
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

class TestMeshyFeederSecurity(unittest.TestCase):
    @patch('requests.post')
    def test_create_meshy_task_timeout(self, mock_post):
        """Test that create_meshy_task passes the API_TIMEOUT to requests.post."""
        mock_post.return_value.status_code = 202
        mock_post.return_value.json.return_value = {'result': 'task_123'}

        feeder.create_meshy_task("data:image/png;base64,abc")

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertIn('timeout', kwargs)
        self.assertEqual(kwargs['timeout'], feeder.API_TIMEOUT)
        self.assertEqual(feeder.API_TIMEOUT, 30)

    @patch('requests.get')
    @patch('time.sleep', return_value=None)
    def test_download_model_timeouts(self, mock_sleep, mock_get):
        """Test that download_model passes correct timeouts to both status check and download calls."""
        # Mocking the two sequential GET calls:
        # 1. Status check -> SUCCEEDED
        # 2. Model download -> binary content
        mock_response_status = MagicMock()
        mock_response_status.json.return_value = {
            'status': 'SUCCEEDED',
            'model_urls': {'glb': 'http://fake.url/model.glb'}
        }

        mock_response_download = MagicMock()
        mock_response_download.content = b"fake_model_binary_data"

        mock_get.side_effect = [mock_response_status, mock_response_download]

        with patch('builtins.open', unittest.mock.mock_open()):
            # We don't care about the actual file writing, just the requests calls
            feeder.download_model("task_123", "test.png")

        self.assertEqual(mock_get.call_count, 2)

        # Check first call (status check)
        _, kwargs0 = mock_get.call_args_list[0]
        self.assertEqual(kwargs0['timeout'], feeder.API_TIMEOUT)

        # Check second call (actual download)
        _, kwargs1 = mock_get.call_args_list[1]
        self.assertEqual(kwargs1['timeout'], feeder.DOWNLOAD_TIMEOUT)
        self.assertEqual(feeder.DOWNLOAD_TIMEOUT, 120)

    @patch('requests.get')
    def test_download_model_api_timeout_exception(self, mock_get):
        """Test that download_model (correctly) lets timeout exceptions bubble up or handle them."""
        # Create a mock exception class since requests is not installed
        class MockTimeout(Exception):
            pass

        # Inject the mock exception into the mocked requests module
        import requests
        requests.exceptions = MagicMock()
        requests.exceptions.Timeout = MockTimeout

        mock_get.side_effect = MockTimeout("Connection timed out")

        with self.assertRaises(MockTimeout):
            feeder.download_model("task_123", "test.png")

    @patch('os.path.getsize')
    def test_get_base64_image_size_limit(self, mock_getsize):
        """Test that get_base64_image raises a ValueError if the file is too large."""
        # Set the mock to return a size larger than the limit
        mock_getsize.return_value = feeder.MAX_IMAGE_SIZE + 1

        with self.assertRaises(ValueError) as context:
            feeder.get_base64_image("dummy.png")

        self.assertIn("exceeds the maximum allowed size", str(context.exception))

if __name__ == '__main__':
    unittest.main()
