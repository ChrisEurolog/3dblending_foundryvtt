import os
import sys
import unittest
import subprocess
from unittest.mock import patch, MagicMock, mock_open, call
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_frozen_with_meipass(self):
        """Test path resolution when frozen (PyInstaller) and _MEIPASS is present."""
        fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))
        fake_meipass = '/tmp/_MEI12345'

        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys.executable = fake_exe
            mock_sys._MEIPASS = fake_meipass

            paths = mp.get_app_paths()

            expected_base = os.path.dirname(fake_exe)
            expected_scripts = fake_meipass

            self.assertEqual(paths.base, expected_base)
            self.assertEqual(paths.scripts, expected_scripts)

    def test_get_app_paths_frozen_without_meipass(self):
        """Test path resolution when frozen but _MEIPASS is missing (fallback)."""
        fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))

        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys.executable = fake_exe
            # Ensure _MEIPASS is not set on the mock
            del mock_sys._MEIPASS

            paths = mp.get_app_paths()

            expected_base = os.path.dirname(fake_exe)
            # Fallback is base_dir
            expected_scripts = expected_base

            self.assertEqual(paths.base, expected_base)
            self.assertEqual(paths.scripts, expected_scripts)

    def test_get_app_paths_not_frozen(self):
        """Test path resolution when running as a script (dev mode)."""
        fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))

        with patch('scripts.main_pipeline.sys') as mock_sys:
            # Simulate not frozen by ensuring the attribute is missing
            del mock_sys.frozen

            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()

                expected_scripts = os.path.dirname(fake_file)
                expected_base = os.path.abspath(os.path.join(expected_scripts, '..'))

                self.assertEqual(paths.scripts, expected_scripts)
                self.assertEqual(paths.base, expected_base)

class TestPipelineInitialization(unittest.TestCase):

    @patch('scripts.main_pipeline.parse_args')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.os.makedirs')
    @patch('scripts.main_pipeline.os.path.exists')
    def test_initialize_pipeline_success(self, mock_exists, mock_makedirs, mock_load_config, mock_get_app_paths, mock_parse_args):
        # Setup mocks
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args

        mock_app_paths = mp.AppPaths(base='/fake/base', scripts='/fake/scripts')
        mock_get_app_paths.return_value = mock_app_paths

        mock_config = {
            'paths': {
                'blender_exe': 'blender',
                'meshopt_exe': 'gltfpack',
                'source_dir': 'source',
                'output_dir': 'output',
                'temp_dir': 'temp'
            }
        }
        mock_load_config.return_value = mock_config
        mock_exists.return_value = True # Source dir exists

        # Execute
        cfg = mp.initialize_pipeline()

        # Verify
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.args, mock_args)
        self.assertEqual(cfg.app_paths, mock_app_paths)
        self.assertEqual(cfg.config, mock_config)
        self.assertEqual(cfg.blender_exe, 'blender')
        self.assertEqual(mock_makedirs.call_count, 2) # output and temp

    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.parse_args')
    @patch('scripts.main_pipeline.input', side_effect=['']) # Mock input for "Press Enter to exit..."
    def test_initialize_pipeline_config_failure(self, mock_input, mock_parse_args, mock_get_app_paths, mock_load_config):
        mock_load_config.return_value = None
        mock_get_app_paths.return_value = mp.AppPaths(base='/fake/base', scripts='/fake/scripts')

        cfg = mp.initialize_pipeline()
        self.assertIsNone(cfg)

    @patch('scripts.main_pipeline.os.makedirs')
    @patch('scripts.main_pipeline.os.path.exists')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.parse_args')
    def test_initialize_pipeline_source_dir_failure(self, mock_parse_args, mock_get_app_paths, mock_load_config, mock_exists, mock_makedirs):
        mock_load_config.return_value = {
            'paths': {
                'blender_exe': 'blender',
                'meshopt_exe': 'gltfpack',
                'source_dir': 'source',
                'output_dir': 'output',
                'temp_dir': 'temp'
            }
        }
        mock_get_app_paths.return_value = mp.AppPaths(base='/fake/base', scripts='/fake/scripts')
        mock_exists.return_value = False
        mock_makedirs.side_effect = [None, None, OSError("Failed to create")] # output, temp, then source

        cfg = mp.initialize_pipeline()
        self.assertIsNone(cfg)

if __name__ == '__main__':
    unittest.main()
