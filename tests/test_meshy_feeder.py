import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Create mock objects
mock_pipeline = MagicMock()
mock_pipeline.get_app_paths.return_value = MagicMock(base='/fake/base', scripts='/fake/scripts')
mock_pipeline.load_config.return_value = {'meshy_api_key': 'fake_key'}
mock_pipeline.resolve_path.return_value = '/fake/export'

mock_requests = MagicMock()
mock_trimesh = MagicMock()
mock_xatlas = MagicMock()
mock_numpy = MagicMock()
mock_bpy = MagicMock()
mock_bmesh = MagicMock()
mock_addon_utils = MagicMock()
mock_pil = MagicMock()

# Instead of keeping a permanent mock in sys.modules, we do it safely inside setUp/tearDown
# However, importing scripts.meshy_feeder requires these modules to be present at import time.
# To safely load the module without polluting sys.modules globally for subsequent test files,
# we add the mocks, import the module, then restore sys.modules.

_saved_modules = {}
_modules_to_mock = {
    'requests': mock_requests,
    'trimesh': mock_trimesh,
    'xatlas': mock_xatlas,
    'numpy': mock_numpy,
    'bpy': mock_bpy,
    'bmesh': mock_bmesh,
    'addon_utils': mock_addon_utils,
    'PIL': mock_pil,
    'scripts.main_pipeline': mock_pipeline
}

for mod_name, mock_mod in _modules_to_mock.items():
    if mod_name in sys.modules:
        _saved_modules[mod_name] = sys.modules[mod_name]
    sys.modules[mod_name] = mock_mod

try:
    import scripts.meshy_feeder as feeder
finally:
    for mod_name in _modules_to_mock:
        if mod_name in _saved_modules:
            sys.modules[mod_name] = _saved_modules[mod_name]
        else:
            del sys.modules[mod_name]

class TestMeshyFeeder(unittest.TestCase):
    def setUp(self):
        # Because we deleted 'requests' from sys.modules after import,
        # feeder.requests still points to mock_requests.
        # We can just reset its mock calls for each test.
        mock_requests.reset_mock()

    def test_create_meshy_task_success(self):
        """Test the successful creation of a Meshy task."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {'result': 'test_task_123'}
        mock_requests.post.return_value = mock_response

        data_uri = "data:image/png;base64,fake_data"
        result = feeder.create_meshy_task(data_uri)

        # Assertions
        self.assertEqual(result, 'test_task_123')
        mock_requests.post.assert_called_once_with(
            "https://api.meshy.ai/v1/image-to-3d",
            headers={"Authorization": f"Bearer {feeder.MESHY_API_KEY}"},
            json={
                "image_url": data_uri,
                "enable_pbr": True,
                "target_polycount": feeder.TARGET_POLYCOUNT,
                "texture_res": feeder.TEXTURE_RES,
                "topology": "quad"
            },
            timeout=feeder.API_TIMEOUT
        )

    def test_create_meshy_task_failure(self):
        """Test failure handling when creating a Meshy task."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.post.return_value = mock_response

        data_uri = "data:image/png;base64,fake_data"
        result = feeder.create_meshy_task(data_uri)

        # Assertions
        self.assertIsNone(result)
        mock_requests.post.assert_called_once()

if __name__ == '__main__':
    unittest.main()
