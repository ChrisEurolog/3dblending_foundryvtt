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

class TestMeshyFeederRetry(unittest.TestCase):
    @patch('requests.get')
    @patch('time.sleep', return_value=None)
    def test_download_model_retry_limit(self, mock_sleep, mock_get):
        """Test that download_model eventually stops polling after a certain number of retries."""
        # Mock API to always return IN_PROGRESS
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'IN_PROGRESS'}
        mock_get.return_value = mock_response

        # Set a reasonable limit for the test
        MAX_RETRIES_TEST = 40
        if not hasattr(feeder, 'MAX_RETRIES'):
            # If not yet implemented, this test will fail by looping
            # until side_effect is exhausted
            pass
        else:
            MAX_RETRIES_TEST = feeder.MAX_RETRIES

        # Provide enough responses to cover the expected limit, plus one to see if it continues
        mock_get.side_effect = [mock_response] * (MAX_RETRIES_TEST + 5)

        result = feeder.download_model("task_123", "test.png")

        # We expect it to return False when it hits the limit
        self.assertFalse(result, "Should return False when retry limit is reached")

        # It should have called the API exactly MAX_RETRIES times
        self.assertEqual(mock_get.call_count, MAX_RETRIES_TEST)

if __name__ == '__main__':
    unittest.main()
