import os
import sys
import unittest
import subprocess
from unittest.mock import patch, MagicMock, mock_open, call
import scripts.main_pipeline as mp

class TestAppPaths(unittest.TestCase):
    def test_get_app_paths_frozen(self):
        """Test path resolution when frozen (PyInstaller)."""
        with patch('sys.frozen', True, create=True), \
             patch('sys.executable', '/tmp/fake_exe'), \
             patch('sys._MEIPASS', '/tmp/_MEI12345', create=True):
            paths = mp.get_app_paths()
            self.assertEqual(paths.base, '/tmp')
            self.assertEqual(paths.scripts, '/tmp/_MEI12345')

    def test_get_app_paths_unfrozen(self):
        """Test path resolution when running from source."""
        # Ensure sys.frozen is False
        with patch('sys.frozen', False, create=True), \
             patch('scripts.main_pipeline.__file__', '/app/scripts/main_pipeline.py'):
            paths = mp.get_app_paths()
            self.assertEqual(paths.base, '/app')
            self.assertEqual(paths.scripts, '/app/scripts')


class TestRunPipeline(unittest.TestCase):
    def setUp(self):
        # Common mocks for run_pipeline tests
        self.mock_config = {
            'paths': {
                'blender_exe': 'blender',
                'meshopt_exe': 'gltfpack',
                'source_dir': 'source',
                'output_dir': 'output',
                'temp_dir': 'temp'
            },
            'profiles': {
                'token_production': {'target_v': 1000, 'res': 1024, 'norm': True, 'matte': False}
            }
        }

    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.argparse.ArgumentParser.parse_args')
    @patch('builtins.input', return_value='')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('os.remove')
    @patch('builtins.print')
    def test_run_pipeline_blender_failure(self, mock_print, mock_remove, mock_listdir, mock_makedirs, mock_exists, mock_input, mock_args, mock_get_app_paths, mock_load_config, mock_subprocess_run):
        """Test that run_pipeline continues after a Blender process failure."""

        # Setup mocks
        mock_args.return_value = MagicMock(mode='batch', profile='token_production', input=None)
        mock_get_app_paths.return_value = mp.AppPaths(base='/app', scripts='/app/scripts')
        mock_load_config.return_value = self.mock_config

        # Simulate two files in source directory
        mock_listdir.return_value = ['file1.glb', 'file2.glb']

        # Paths exist
        mock_exists.return_value = True

        # Simulate failure on first file, success on second
        def side_effect(cmd, check=True):
            # Check if this is a blender command
            # cmd is a list, e.g. ['blender', '--background', ...]
            # The input file is at a specific index or we check all args
            if 'blender' in cmd[0]:
                if any('file1.glb' in arg for arg in cmd):
                    raise subprocess.CalledProcessError(1, cmd)
                if any('file2.glb' in arg for arg in cmd):
                    return MagicMock() # Success
            return MagicMock() # For other commands like meshopt if called

        mock_subprocess_run.side_effect = side_effect

        # Run pipeline
        mp.run_pipeline()

        # Verify
        # Should have called subprocess.run for both files (Blender pass)
        # Even though first failed, loop should continue to second.

        # Count blender calls
        blender_calls = [c for c in mock_subprocess_run.call_args_list if 'blender' in c[0][0][0]]
        self.assertEqual(len(blender_calls), 2, "Should attempt to process both files despite failure on first")

        # Verify error message for first file
        found_error = False
        for call_args in mock_print.call_args_list:
            msg = str(call_args)
            if "Blender Error" in msg and "file1.glb" in msg:
                found_error = True
                break
        self.assertTrue(found_error, "Should log error for failed file")

    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.argparse.ArgumentParser.parse_args')
    @patch('builtins.input', return_value='')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('builtins.print')
    def test_run_pipeline_blender_not_found(self, mock_print, mock_listdir, mock_makedirs, mock_exists, mock_input, mock_args, mock_get_app_paths, mock_load_config, mock_subprocess_run):
        """Test that run_pipeline exits if Blender executable is not found (FileNotFoundError)."""

        # Setup mocks
        mock_args.return_value = MagicMock(mode='single', profile='token_production', input='test.glb')
        mock_get_app_paths.return_value = mp.AppPaths(base='/app', scripts='/app/scripts')
        mock_load_config.return_value = self.mock_config

        mock_exists.return_value = True

        # Simulate FileNotFoundError when running blender
        mock_subprocess_run.side_effect = FileNotFoundError("Blender not found")

        # Run pipeline
        mp.run_pipeline()

        # Verify
        # Should catch FileNotFoundError and print error message, then return.

        # Verify error message
        found_error = False
        for call_args in mock_print.call_args_list:
            if "Blender executable not found" in str(call_args):
                found_error = True
                break
        self.assertTrue(found_error, "Should log error for missing Blender executable")

    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.argparse.ArgumentParser.parse_args')
    @patch('builtins.input', return_value='')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.listdir')
    @patch('builtins.print')
    def test_run_pipeline_blender_not_found_batch(self, mock_print, mock_listdir, mock_makedirs, mock_exists, mock_input, mock_args, mock_get_app_paths, mock_load_config, mock_subprocess_run):
        """Test that run_pipeline exits if Blender executable is not found in batch mode."""

        # Setup mocks
        mock_args.return_value = MagicMock(mode='batch', profile='token_production', input=None)
        mock_get_app_paths.return_value = mp.AppPaths(base='/app', scripts='/app/scripts')
        mock_load_config.return_value = self.mock_config

        mock_listdir.return_value = ['file1.glb', 'file2.glb']
        mock_exists.return_value = True

        # Simulate FileNotFoundError
        mock_subprocess_run.side_effect = FileNotFoundError("Blender not found")

        # Run pipeline
        mp.run_pipeline()

        # Verify
        # Should only attempt once because it returns on FileNotFoundError
        blender_calls = [c for c in mock_subprocess_run.call_args_list if 'blender' in c[0][0][0]]
        self.assertEqual(len(blender_calls), 1, "Should stop processing after finding Blender executable missing")


if __name__ == '__main__':
    unittest.main()
