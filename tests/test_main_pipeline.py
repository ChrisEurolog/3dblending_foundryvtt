import os
import sys
import unittest
import json
from unittest.mock import patch, mock_open, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_not_frozen(self):
        # Ensure frozen is not present or False
        with patch.dict(sys.__dict__):
            if 'frozen' in sys.__dict__:
                del sys.frozen

            fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()
                expected_scripts = os.path.dirname(fake_file)
                expected_base = os.path.abspath(os.path.join(expected_scripts, '..'))

                self.assertEqual(paths.scripts, expected_scripts)
                self.assertEqual(paths.base, expected_base)

    def test_get_app_paths_frozen(self):
        fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))
        fake_meipass = '/tmp/_MEI12345'

        mock_dict = {
            'frozen': True,
            'executable': fake_exe,
            '_MEIPASS': fake_meipass
        }

        with patch.dict(sys.__dict__, mock_dict, clear=False):
            paths = mp.get_app_paths()
            expected_base = os.path.dirname(fake_exe)
            expected_scripts = fake_meipass

            self.assertEqual(paths.base, expected_base)
            self.assertEqual(paths.scripts, expected_scripts)

    def test_get_app_paths_frozen_no_meipass(self):
        fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))

        mock_dict = {
            'frozen': True,
            'executable': fake_exe
        }

        with patch.dict(sys.__dict__, mock_dict, clear=False):
            # Ensure _MEIPASS is removed if it existed
            if '_MEIPASS' in sys.__dict__:
                del sys._MEIPASS

            paths = mp.get_app_paths()
            expected_base = os.path.dirname(fake_exe)
            expected_scripts = expected_base

            self.assertEqual(paths.base, expected_base)
            self.assertEqual(paths.scripts, expected_scripts)

    @patch('os.path.exists')
    def test_load_config_valid(self, mock_exists):
        base_dir = '/fake/base'
        config_data = {"key": "value"}
        json_content = json.dumps(config_data)

        mock_exists.return_value = True

        with patch('builtins.open', mock_open(read_data=json_content)):
            config = mp.load_config(base_dir)
            self.assertEqual(config, config_data)

    @patch('os.path.exists')
    def test_load_config_missing(self, mock_exists):
        base_dir = '/fake/base'
        mock_exists.return_value = False

        # Capture stdout to avoid clutter
        with patch('sys.stdout', new_callable=MagicMock):
            config = mp.load_config(base_dir)
            self.assertIsNone(config)

    @patch('os.path.exists')
    def test_load_config_invalid_json(self, mock_exists):
        base_dir = '/fake/base'
        mock_exists.return_value = True

        # Invalid JSON content
        invalid_json = "{ key: value "

        with patch('builtins.open', mock_open(read_data=invalid_json)):
             # Expect graceful failure (return None) instead of crash
             # Also verify it prints an error message, but simpler to just check return value
             with patch('sys.stdout', new_callable=MagicMock):
                 config = mp.load_config(base_dir)
                 self.assertIsNone(config)

if __name__ == '__main__':
    unittest.main()
