import os
import sys
import unittest
import json
from unittest.mock import patch, mock_open
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    # --- Path Resolution Tests ---

    def test_get_app_paths_dev(self):
        """Test path resolution in development mode (not frozen)."""
        with patch.dict(sys.__dict__, {'frozen': False}):
            paths = mp.get_app_paths()

            actual_file = os.path.abspath(mp.__file__)
            expected_scripts = os.path.dirname(actual_file)
            expected_base = os.path.abspath(os.path.join(expected_scripts, '..'))

            self.assertEqual(paths.scripts, expected_scripts)
            self.assertEqual(paths.base, expected_base)

    def test_get_app_paths_frozen_with_meipass(self):
        """Test path resolution in frozen mode with sys._MEIPASS."""
        fake_exe = '/home/user/repo/dist/main_pipeline.exe'
        fake_meipass = '/tmp/_MEI12345'
        with patch.dict(sys.__dict__, {'frozen': True, 'executable': fake_exe, '_MEIPASS': fake_meipass}):
            paths = mp.get_app_paths()
            self.assertEqual(paths.scripts, fake_meipass)
            self.assertEqual(paths.base, os.path.dirname(fake_exe))

    def test_get_app_paths_frozen_no_meipass(self):
        """Test path resolution in frozen mode without sys._MEIPASS."""
        fake_exe = '/home/user/repo/dist/main_pipeline.exe'
        with patch.dict(sys.__dict__, {'frozen': True, 'executable': fake_exe}):
            # Ensure _MEIPASS is absent during the test
            with patch.dict(sys.__dict__):
                if '_MEIPASS' in sys.__dict__:
                    del sys._MEIPASS
                paths = mp.get_app_paths()
                self.assertEqual(paths.scripts, os.path.dirname(fake_exe))
                self.assertEqual(paths.base, os.path.dirname(fake_exe))

    def test_resolve_path_absolute(self):
        abs_path = os.path.abspath('/some/path')
        self.assertEqual(mp.resolve_path(abs_path, '/root'), abs_path)

    def test_resolve_path_relative(self):
        root = '/root'
        rel_path = 'subdir/file.txt'
        expected = os.path.normpath(os.path.join(root, rel_path))
        self.assertEqual(mp.resolve_path(rel_path, root), expected)

    # --- Config Loading Tests ---

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"paths": {"blender_exe": "blender"}}')
    def test_load_config_success(self, mock_file, mock_exists):
        mock_exists.return_value = True
        config = mp.load_config('/fake/dir')

        self.assertIsNotNone(config)
        self.assertEqual(config['paths']['blender_exe'], 'blender')
        expected_path = os.path.normpath('/fake/dir/axiom_config.json')
        mock_exists.assert_called_with(expected_path)
        mock_file.assert_called_with(expected_path)

    @patch('os.path.exists')
    def test_load_config_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        with patch('builtins.print') as mock_print:
            config = mp.load_config('/fake/dir')
            self.assertIsNone(config)
            mock_print.assert_called()

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{invalid_json}')
    def test_load_config_invalid_json(self, mock_file, mock_exists):
        mock_exists.return_value = True
        with self.assertRaises(json.JSONDecodeError):
            mp.load_config('/fake/dir')

if __name__ == '__main__':
    unittest.main()
