import os
import sys
import unittest
import json
from unittest.mock import patch, mock_open
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_frozen(self):
        """Test get_app_paths when sys.frozen is True (PyInstaller)."""
        mock_values = {
            'frozen': True,
            'executable': os.path.join('/app', 'run'),
            '_MEIPASS': '/tmp/_MEI12345'
        }
        with patch.dict(sys.__dict__, mock_values):
            paths = mp.get_app_paths()
            self.assertEqual(paths.base, os.path.dirname(mock_values['executable']))
            self.assertEqual(paths.scripts, mock_values['_MEIPASS'])

    def test_get_app_paths_frozen_no_meipass(self):
        """Test get_app_paths when frozen but _MEIPASS is missing (fallback)."""
        mock_values = {
            'frozen': True,
            'executable': os.path.join('/app', 'run')
        }
        # Ensure _MEIPASS is not present
        with patch.dict(sys.__dict__, mock_values):
            if hasattr(sys, '_MEIPASS'):
                del sys._MEIPASS

            paths = mp.get_app_paths()
            self.assertEqual(paths.base, os.path.dirname(mock_values['executable']))
            # If _MEIPASS is missing, it falls back to base_dir
            self.assertEqual(paths.scripts, paths.base)

    def test_get_app_paths_dev(self):
        """Test get_app_paths in development environment."""
        with patch.dict(sys.__dict__):
            if hasattr(sys, 'frozen'):
                del sys.frozen

            # Mock __file__
            fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))

            # We need to patch mp.__file__ but mp is the module object.
            # The function uses __file__ which resolves to the module's __file__.
            # However, inside the function, it uses `__file__`.
            # If we imported the function, `__file__` is bound to the module's scope.
            # Patching `scripts.main_pipeline.__file__` should work.

            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()
                expected_script_dir = os.path.dirname(fake_file)
                expected_base_dir = os.path.abspath(os.path.join(expected_script_dir, '..'))

                self.assertEqual(paths.scripts, expected_script_dir)
                self.assertEqual(paths.base, expected_base_dir)

    def test_resolve_path_absolute(self):
        """Test resolve_path with an absolute path."""
        abs_path = os.path.abspath('some/file.txt')
        root_dir = os.path.abspath('root')
        result = mp.resolve_path(abs_path, root_dir)
        self.assertEqual(result, abs_path)

    def test_resolve_path_relative(self):
        """Test resolve_path with a relative path."""
        rel_path = os.path.join('some', 'file.txt')
        root_dir = os.path.abspath('root')
        result = mp.resolve_path(rel_path, root_dir)
        expected = os.path.normpath(os.path.join(root_dir, rel_path))
        self.assertEqual(result, expected)

    def test_load_config_success(self):
        """Test load_config successfully reads a config file."""
        base_dir = '/app'
        config_data = {'key': 'value'}
        mock_json_content = json.dumps(config_data)

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_json_content)):
                # We also assume json.load works with mock_open
                config = mp.load_config(base_dir)
                self.assertEqual(config, config_data)

    def test_load_config_file_not_found(self):
        """Test load_config returns None when file does not exist."""
        base_dir = '/app'
        with patch('os.path.exists', return_value=False):
            with patch('builtins.print'):
                config = mp.load_config(base_dir)
                self.assertIsNone(config)

if __name__ == '__main__':
    unittest.main()
