import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import argparse

# Ensure we can import from scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_dev(self):
        # In dev mode (not frozen)
        with patch('sys.frozen', False, create=True):
             paths = mp.get_app_paths()
             # scripts dir should end with 'scripts'
             self.assertTrue(paths.scripts.endswith('scripts'))
             # base dir is parent of scripts
             self.assertTrue(os.path.isdir(paths.base))

    def test_get_app_paths_frozen(self):
        # In frozen mode
        with patch('sys.frozen', True, create=True):
            with patch('sys.executable', '/dist/exe'):
                with patch('sys._MEIPASS', '/tmp/mei', create=True):
                    paths = mp.get_app_paths()
                    self.assertEqual(paths.base, '/dist')
                    self.assertEqual(paths.scripts, '/tmp/mei')

    def test_parse_args(self):
        with patch('argparse.ArgumentParser.parse_args') as mock_parse:
            mp.parse_args()
            mock_parse.assert_called_once()

    def test_get_processing_mode_arg(self):
        self.assertEqual(mp.get_processing_mode('batch'), 'batch')

    @patch('builtins.input', return_value='1')
    def test_get_processing_mode_interactive_single(self, mock_input):
        self.assertEqual(mp.get_processing_mode(None), 'single')

    @patch('builtins.input', return_value='2')
    def test_get_processing_mode_interactive_batch(self, mock_input):
        self.assertEqual(mp.get_processing_mode(None), 'batch')

    def test_select_profile_arg(self):
        profiles = {'p1': {}, 'p2': {}}
        self.assertEqual(mp.select_profile(profiles, 'p1'), 'p1')

    @patch('builtins.input', side_effect=['1'])
    def test_select_profile_interactive(self, mock_input):
        profiles = {'p1': {'target_v': 100, 'res': 1024}, 'p2': {'target_v': 200, 'res': 2048}}
        # Dictionary iteration order is guaranteed in recent Python
        self.assertEqual(mp.select_profile(profiles, None), 'p1')

    @patch('builtins.input', side_effect=['invalid', '2'])
    def test_select_profile_interactive_retry(self, mock_input):
        profiles = {'p1': {'target_v': 100, 'res': 1024}, 'p2': {'target_v': 200, 'res': 2048}}
        self.assertEqual(mp.select_profile(profiles, None), 'p2')

    @patch('builtins.input', return_value='')
    def test_confirm_settings_default(self, mock_input):
        profile = {'target_v': 100, 'res': 1024}
        v, res = mp.confirm_settings('p1', profile)
        self.assertEqual(v, 100)
        self.assertEqual(res, 1024)

    @patch('builtins.input', side_effect=['edit', '500', '256'])
    def test_confirm_settings_edit(self, mock_input):
        profile = {'target_v': 100, 'res': 1024}
        v, res = mp.confirm_settings('p1', profile)
        self.assertEqual(v, 500)
        self.assertEqual(res, 256)

    @patch('os.listdir', return_value=['a.glb', 'b.txt'])
    def test_get_files_to_process_batch(self, mock_listdir):
        files = mp.get_files_to_process('batch', None, '/source')
        self.assertEqual(files, ['a.glb'])

    def test_get_files_to_process_single_arg(self):
        files = mp.get_files_to_process('single', 'myfile', '/source')
        self.assertEqual(files, ['myfile.glb'])

    @patch('builtins.input', return_value='userfile')
    def test_get_files_to_process_single_interactive(self, mock_input):
        files = mp.get_files_to_process('single', None, '/source')
        self.assertEqual(files, ['userfile.glb'])

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.remove')
    @patch('shutil.copy')
    def test_process_file_success(self, mock_copy, mock_remove, mock_exists, mock_run):
        # Setup
        mock_exists.return_value = True # All files exist
        profile_data = {'norm': 1, 'matte': 1}
        app_paths = mp.AppPaths(base='/base', scripts='/scripts')

        mp.process_file('test.glb', '/source', '/temp', '/out', 'blender', 'meshopt',
                        profile_data, 1000, 1024, app_paths, 'production')

        # Checks
        self.assertEqual(mock_run.call_count, 2) # Blender + Meshopt
        mock_remove.assert_called_once() # Cleanup

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_process_file_missing_input(self, mock_exists, mock_run):
        # input file does not exist
        mock_exists.side_effect = lambda p: not p.endswith('test.glb')

        profile_data = {'norm': 1, 'matte': 1}
        app_paths = mp.AppPaths(base='/base', scripts='/scripts')

        mp.process_file('test.glb', '/source', '/temp', '/out', 'blender', 'meshopt',
                        profile_data, 1000, 1024, app_paths, 'production')

        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_process_file_blender_worker_missing(self, mock_exists, mock_run):
        # blender_worker.py does not exist
        # exists calls: input_path (True), blender_worker (False)
        def side_effect(p):
            if p.endswith('blender_worker.py'):
                return False
            return True
        mock_exists.side_effect = side_effect

        profile_data = {'norm': 1, 'matte': 1}
        app_paths = mp.AppPaths(base='/base', scripts='/scripts')

        with self.assertRaises(FileNotFoundError):
            mp.process_file('test.glb', '/source', '/temp', '/out', 'blender', 'meshopt',
                            profile_data, 1000, 1024, app_paths, 'production')

if __name__ == '__main__':
    unittest.main()
