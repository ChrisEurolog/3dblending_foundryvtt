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

    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('builtins.print')
    def test_run_pipeline_missing_blender(self, mock_print, mock_get_app_paths, mock_load_config, mock_subprocess_run):
        """Test run_pipeline exits or logs when blender_exe is missing (throws OSError)."""
        mock_app_paths = MagicMock()
        mock_app_paths.base = '/mock/base'
        mock_get_app_paths.return_value = mock_app_paths

        mock_load_config.return_value = {
            'paths': {
                'blender_exe': 'fake_blender',
                'instant_meshes_exe': 'fake_instant_meshes',
                'xnormal_exe': 'fake_xnormal',
                'gltfpack_exe': 'fake_gltfpack',
                'source_dir': '/mock/source',
                'output_dir': '/mock/output',
                'temp_dir': '/mock/temp'
            },
            'profiles': {
                'token_production': {'target_v': 1000, 'res': 1024}
            }
        }

        mock_subprocess_run.side_effect = OSError("Mock OS Error")

        with patch('scripts.main_pipeline.parse_args') as mock_parse_args:
            with patch('scripts.main_pipeline.os.makedirs'):
                with patch('scripts.main_pipeline.os.path.exists', return_value=True):
                    mock_parse_args.return_value = MagicMock()
                    mp.run_pipeline()

        expected_path = 'fake_blender'  # It does not call resolve_path on blender_exe in main_pipeline.py
        mock_print.assert_any_call(f"❌ Error: Blender executable not found at '{expected_path}'. Please check config.json.")

    @patch('scripts.main_pipeline.shutil.which')
    @patch('scripts.main_pipeline.os.path.exists')
    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('builtins.print')
    def test_run_pipeline_missing_instant_meshes(self, mock_print, mock_get_app_paths, mock_load_config, mock_subprocess_run, mock_os_path_exists, mock_which):
        """Test run_pipeline exits or logs when instant_meshes_exe is missing."""
        mock_app_paths = MagicMock()
        mock_app_paths.base = '/mock/base'
        mock_get_app_paths.return_value = mock_app_paths

        mock_load_config.return_value = {
            'paths': {
                'blender_exe': 'fake_blender',
                'instant_meshes_exe': 'fake_instant_meshes',
                'xnormal_exe': 'fake_xnormal',
                'gltfpack_exe': 'fake_gltfpack',
                'source_dir': '/mock/source',
                'output_dir': '/mock/output',
                'temp_dir': '/mock/temp'
            },
            'profiles': {
                'token_production': {'target_v': 1000, 'res': 1024}
            }
        }

        # Blender run succeeds
        mock_subprocess_run.return_value = MagicMock()

        # Mock os.path.exists to return False for instant_meshes_exe
        def fake_exists(path):
            if path.endswith('fake_instant_meshes'):
                return False
            return True
        mock_os_path_exists.side_effect = fake_exists

        # Mock shutil.which to return False
        mock_which.return_value = False

        with patch('scripts.main_pipeline.parse_args') as mock_parse_args:
            with patch('scripts.main_pipeline.os.makedirs'):
                mock_parse_args.return_value = MagicMock()
                mp.run_pipeline()

        # The expected path might be resolved.
        expected_path = os.path.normpath('/mock/base/fake_instant_meshes')
        mock_print.assert_any_call(f"❌ Error: Instant Meshes executable not found at '{expected_path}'. Please check config.json.")


    @patch('scripts.main_pipeline.os.path.exists')
    @patch('scripts.main_pipeline.os.remove')
    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.unwrap_and_bake')
    @patch('scripts.main_pipeline.shutil.copy')
    @patch('scripts.main_pipeline.shutil.move')
    @patch('builtins.print')
    def test_process_file_unwrap_and_bake_failure(self, mock_print, mock_move, mock_copy, mock_unwrap_and_bake, mock_run, mock_remove, mock_exists):
        """Test process_file handles unwrapping and baking failure."""
        mock_exists.return_value = True

        mock_unwrap_and_bake.return_value = False

        app_paths = MagicMock()
        app_paths.scripts = '/scripts'

        profile_data = {'norm': 1, 'matte': 1}

        result = mp.process_file(
            f="test.glb",
            source_dir="/source",
            temp_dir="/temp",
            output_dir="/output",
            blender_exe="blender",
            instant_meshes_exe="instantmeshes",
            xnormal_exe="xnormal",
            gltfpack_exe="gltfpack",
            profile_data=profile_data,
            target_v=1000,
            max_res=1024,
            app_paths=app_paths,
            profile_key="token_production",
            archive_dir="/archive"
        )

        # Verify that process_file returned False
        self.assertFalse(result)

        # Verify that unwrap_and_bake was called
        mock_unwrap_and_bake.assert_called_once()

        # Verify that an error message was printed
        mock_print.assert_any_call("❌ Texture baking failed. Aborting processing for this file.")

        # Because unwrap and bake failed, move should NOT be called
        mock_move.assert_not_called()

    @patch('scripts.main_pipeline.os.path.exists')
    @patch('scripts.main_pipeline.subprocess.run')
    @patch('builtins.print')
    def test_process_file_instant_meshes_failure(self, mock_print, mock_run, mock_exists):
        """Test process_file returns False and logs error when Instant Meshes fails."""
        mock_exists.return_value = True

        def mock_subprocess_run(cmd, *args, **kwargs):
            if cmd and cmd[0] == "instantmeshes":
                raise subprocess.CalledProcessError(1, cmd, "Mock Instant Meshes Error")
            return MagicMock()

        mock_run.side_effect = mock_subprocess_run

        app_paths = MagicMock()
        app_paths.scripts = '/scripts'
        profile_data = {'target_v': 1000, 'res': 1024}

        result = mp.process_file(
            f="test.glb",
            source_dir="/source",
            temp_dir="/temp",
            output_dir="/output",
            blender_exe="blender",
            instant_meshes_exe="instantmeshes",
            xnormal_exe="xnormal",
            gltfpack_exe="gltfpack",
            profile_data=profile_data,
            target_v=1000,
            max_res=1024,
            app_paths=app_paths,
            profile_key="token_production",
            archive_dir="/archive"
        )

        self.assertFalse(result)

        # Verify the specific error message was printed
        error_msg_found = any("❌ Error running Instant Meshes:" in call_args[0][0] for call_args in mock_print.call_args_list)
        self.assertTrue(error_msg_found, "Expected Instant Meshes error message was not printed.")


if __name__ == '__main__':
    unittest.main()
