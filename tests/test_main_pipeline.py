import os
import sys
import unittest
from unittest.mock import patch
from scripts import main_pipeline

class TestPathResolution(unittest.TestCase):
    def test_get_app_paths_dev(self):
        """Test path resolution in development mode (not frozen)."""
        with patch('sys.frozen', False, create=True):
            paths = main_pipeline.get_app_paths()

            actual_file = os.path.abspath(main_pipeline.__file__)
            expected_scripts = os.path.dirname(actual_file)
            expected_base = os.path.abspath(os.path.join(expected_scripts, '..'))

            self.assertEqual(paths.scripts, expected_scripts)
            self.assertEqual(paths.base, expected_base)

    def test_get_app_paths_frozen_with_meipass(self):
        """Test path resolution in frozen mode with sys._MEIPASS."""
        with patch('sys.frozen', True, create=True):
            with patch('sys.executable', '/home/user/repo/dist/main_pipeline.exe'):
                with patch('sys._MEIPASS', '/tmp/_MEI12345', create=True):
                    paths = main_pipeline.get_app_paths()
                    self.assertEqual(paths.scripts, '/tmp/_MEI12345')
                    self.assertEqual(paths.base, '/home/user/repo/dist')

    @patch('sys.frozen', True, create=True)
    @patch('sys.executable', '/home/user/repo/dist/main_pipeline.exe')
    def test_get_app_paths_frozen_no_meipass(self):
        """Test path resolution in frozen mode without sys._MEIPASS."""
        # Temporarily remove _MEIPASS if it exists
        meipass = getattr(sys, '_MEIPASS', None)
        if hasattr(sys, '_MEIPASS'):
            del sys._MEIPASS

        try:
            paths = main_pipeline.get_app_paths()
            self.assertEqual(paths.scripts, '/home/user/repo/dist')
            self.assertEqual(paths.base, '/home/user/repo/dist')
        finally:
            if meipass is not None:
                sys._MEIPASS = meipass

    @patch('scripts.main_pipeline.tempfile.mkdtemp')
    @patch('scripts.main_pipeline.shutil.rmtree')
    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.os.path.exists')
    @patch('scripts.main_pipeline.os.makedirs')
    @patch('scripts.main_pipeline.load_config')
    @patch('argparse.ArgumentParser.parse_args')
    def test_run_pipeline_secure_temp_creation(self, mock_args, mock_load_config, mock_makedirs, mock_exists, mock_run, mock_rmtree, mock_mkdtemp):
        import argparse
        # Setup mocks
        mock_args.return_value = argparse.Namespace(mode='single', profile='token_production', input='test.glb')

        mock_load_config.return_value = {
            'paths': {
                'blender_exe': 'blender',
                'meshopt_exe': 'meshopt',
                'source_dir': 'source',
                'output_dir': 'output',
                'temp_dir': 'temp'
            },
            'profiles': {
                'token_production': {'target_v': 1000, 'res': 1024, 'norm': 1, 'matte': 1}
            }
        }

        # Mock exists to pass checks
        mock_exists.return_value = True

        # Mock mkdtemp to return a known path
        secure_temp_dir = os.path.join(os.getcwd(), 'secure_temp')
        mock_mkdtemp.return_value = secure_temp_dir

        # Run pipeline
        with patch('builtins.print'): # Silence output
            with patch('builtins.input', return_value=''): # Handle possible input calls
                 main_pipeline.run_pipeline()

        # Verify mkdtemp called
        mock_mkdtemp.assert_called()

        # Verify rmtree called with secure_temp_dir
        mock_rmtree.assert_called_with(secure_temp_dir, ignore_errors=True)

        # Verify subprocess called with path inside secure_temp_dir
        expected_temp_out = os.path.join(secure_temp_dir, 'test.glb')

        # Check args of subprocess.run
        # We expect at least one call (Blender)
        self.assertTrue(mock_run.call_count >= 1)

        # Check Blender call arguments
        args, _ = mock_run.call_args_list[0]
        cmd = args[0]
        self.assertIn(expected_temp_out, cmd)

if __name__ == '__main__':
    unittest.main()
