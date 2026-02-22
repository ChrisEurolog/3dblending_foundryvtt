import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_not_frozen(self):
        # Simulate dev environment
        with patch.dict(sys.__dict__, {'frozen': False}):
            fake_file = os.path.abspath(os.path.join('/app/scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()

                expected_script_dir = os.path.dirname(fake_file)
                expected_base_dir = os.path.abspath(os.path.join(expected_script_dir, '..'))

                self.assertEqual(paths.scripts, expected_script_dir)
                self.assertEqual(paths.base, expected_base_dir)

    def test_get_app_paths_frozen_meipass(self):
        # Simulate PyInstaller environment with _MEIPASS
        fake_exe = '/app/dist/myapp'
        fake_meipass = '/tmp/_MEI12345'

        with patch.dict(sys.__dict__, {'frozen': True, 'executable': fake_exe, '_MEIPASS': fake_meipass}):
            paths = mp.get_app_paths()

            expected_base_dir = os.path.dirname(fake_exe)
            expected_script_dir = fake_meipass

            self.assertEqual(paths.base, expected_base_dir)
            self.assertEqual(paths.scripts, expected_script_dir)

    def test_get_app_paths_frozen_no_meipass(self):
        # Simulate PyInstaller environment without _MEIPASS (fallback)
        fake_exe = '/app/dist/myapp'

        # Ensure _MEIPASS is not present in the environment for this test
        has_meipass = hasattr(sys, '_MEIPASS')
        original_meipass = getattr(sys, '_MEIPASS', None)

        if has_meipass:
             del sys._MEIPASS

        try:
            with patch.dict(sys.__dict__, {'frozen': True, 'executable': fake_exe}):
                paths = mp.get_app_paths()

                expected_base_dir = os.path.dirname(fake_exe)
                expected_script_dir = expected_base_dir # Fallback

                self.assertEqual(paths.base, expected_base_dir)
                self.assertEqual(paths.scripts, expected_script_dir)
        finally:
            if has_meipass:
                sys._MEIPASS = original_meipass

class TestSubprocessSecurity(unittest.TestCase):
    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.os.path.exists')
    @patch('scripts.main_pipeline.os.makedirs')
    @patch('scripts.main_pipeline.os.listdir')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.os.remove')
    @patch('scripts.main_pipeline.shutil.copy')
    @patch('builtins.input', return_value='')
    def test_subprocess_shell_false(self, mock_input, mock_copy, mock_remove, mock_get_app_paths, mock_load_config, mock_listdir, mock_makedirs, mock_exists, mock_run):
        # Setup mocks
        mock_paths = MagicMock()
        mock_paths.base = '/base'
        mock_paths.scripts = '/scripts'
        mock_get_app_paths.return_value = mock_paths

        mock_config = {
            'paths': {
                'blender_exe': 'blender',
                'meshopt_exe': 'meshopt',
                'source_dir': 'source',
                'output_dir': 'output',
                'temp_dir': 'temp'
            },
            'profiles': {
                'token_production': {
                    'target_v': 1000,
                    'res': 1024,
                    'norm': True,
                    'matte': False
                }
            }
        }
        mock_load_config.return_value = mock_config

        # Mock file existence
        # We need source_dir to exist, input file to exist, blender_worker to exist, meshopt_exe to exist
        def side_effect_exists(path):
            return True
        mock_exists.side_effect = side_effect_exists

        # Mock listdir to return one file
        mock_listdir.return_value = ['test.glb']

        # Mock sys.argv to run in batch mode with token_production profile
        with patch.object(sys, 'argv', ['main_pipeline.py', '--mode', 'batch', '--profile', 'token_production']):
            mp.run_pipeline()

        # Check subprocess.run calls
        # We expect 2 calls: one for blender, one for meshopt
        self.assertEqual(mock_run.call_count, 2)

        # Check args for first call (Blender)
        args, kwargs = mock_run.call_args_list[0]
        # Verify shell=False is explicitly passed
        self.assertIn('shell', kwargs, "shell=False should be explicitly set for Blender pass")
        self.assertFalse(kwargs['shell'], "shell argument must be False")

        # Check args for second call (Meshopt)
        args, kwargs = mock_run.call_args_list[1]
        self.assertIn('shell', kwargs, "shell=False should be explicitly set for Meshopt pass")
        self.assertFalse(kwargs['shell'], "shell argument must be False")

if __name__ == '__main__':
    unittest.main()
