import os
import sys
import unittest
import json
from unittest.mock import patch, mock_open, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    @patch('scripts.main_pipeline.os.path.exists')
    @patch('builtins.print')
    def test_load_config_invalid_json(self, mock_print, mock_exists):
        """Test load_config handles invalid JSON by returning None and printing an error."""
        mock_exists.return_value = True

        # mock_open reads invalid JSON
        m = mock_open(read_data='{ "invalid_json": ')
        with patch('builtins.open', m):
            result = mp.load_config('/fake/dir')

        self.assertIsNone(result)
        mock_print.assert_called_with("❌ Error: Config file is not valid JSON.")

    def test_get_app_paths_frozen_with_meipass(self):
        """Test path resolution when frozen (PyInstaller) and _MEIPASS is present."""
        fake_file = os.path.abspath(os.path.join('path', 'to', 'exe'))
        fake_meipass = '/tmp/_MEI12345'

        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys.executable = fake_file
            mock_sys._MEIPASS = fake_meipass

    def test_get_app_paths_dev(self):
        """Test path resolution in development mode (not frozen)."""
        with patch.dict(sys.__dict__, {'frozen': False}):
            paths = mp.get_app_paths()

            actual_file = os.path.abspath(mp.__file__)
            expected_scripts = os.path.dirname(actual_file)
            expected_base = os.path.abspath(os.path.join(expected_scripts, '..'))

            self.assertEqual(paths.scripts, expected_scripts)
            self.assertEqual(paths.base, expected_base)

    def test_parse_args_no_arguments(self):
        """Test parse_args when no arguments are provided."""
        with patch('sys.argv', ['main_pipeline.py']):
            args = mp.parse_args()
            self.assertIsNone(args.mode)
            self.assertIsNone(args.profile)
            self.assertIsNone(args.input)
            self.assertFalse(args.auto)

    def test_get_app_paths_not_frozen(self):
        """Test path resolution when running as a script (dev mode)."""
        fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))

        with patch('scripts.main_pipeline.sys') as mock_sys:
            # Simulate not frozen by ensuring the attribute is missing
            del mock_sys.frozen

            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()
                self.assertEqual(paths.scripts, os.path.dirname(fake_file))
                self.assertEqual(paths.base, os.path.abspath(os.path.join(os.path.dirname(fake_file), '..')))

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
    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open, read_data='{invalid_json}')
    def test_load_config_invalid_json_2(self, mock_file, mock_print, mock_exists):
        mock_exists.return_value = True
        result = mp.load_config('/fake/dir')
        self.assertIsNone(result)
        mock_print.assert_any_call("❌ Error: Config file is not valid JSON.")

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


    @patch('builtins.print')
    def test_confirm_settings_auto(self, mock_print):
        """Test confirm_settings with auto=True."""
        profile_key = "test_profile"
        profile_data = {'target_v': 1000, 'res': 1024}

        result = mp.confirm_settings(profile_key, profile_data, auto=True)

        self.assertEqual(result, (1000, 1024))
        mock_print.assert_called()

    @patch('builtins.print')
    @patch('builtins.input', return_value="")
    def test_confirm_settings_defaults(self, mock_input, mock_print):
        """Test confirm_settings when user chooses defaults (presses Enter)."""
        profile_key = "test_profile"
        profile_data = {'target_v': 1000, 'res': 1024}

        result = mp.confirm_settings(profile_key, profile_data, auto=False)

        self.assertEqual(result, (1000, 1024))
        mock_input.assert_called_once()

    @patch('builtins.print')
    @patch('builtins.input', side_effect=["edit", "2000", "2048"])
    def test_confirm_settings_edit_all(self, mock_input, mock_print):
        """Test confirm_settings when user edits both values."""
        profile_key = "test_profile"
        profile_data = {'target_v': 1000, 'res': 1024}

        result = mp.confirm_settings(profile_key, profile_data, auto=False)

        self.assertEqual(result, (2000, 2048))
        self.assertEqual(mock_input.call_count, 3)

    @patch('builtins.print')
    @patch('builtins.input', side_effect=["edit", "", "2048"])
    def test_confirm_settings_edit_res_only(self, mock_input, mock_print):
        """Test confirm_settings when user edits only resolution."""
        profile_key = "test_profile"
        profile_data = {'target_v': 1000, 'res': 1024}

        result = mp.confirm_settings(profile_key, profile_data, auto=False)

        self.assertEqual(result, (1000, 2048))
        self.assertEqual(mock_input.call_count, 3)

    @patch('builtins.print')
    @patch('builtins.input', side_effect=["edit", "invalid", "2048"])
    def test_confirm_settings_invalid_input(self, mock_input, mock_print):
        """Test confirm_settings handles invalid (non-numeric) input."""
        profile_key = "test_profile"
        profile_data = {'target_v': 1000, 'res': 1024}

        result = mp.confirm_settings(profile_key, profile_data, auto=False)

        # Should fall back to defaults on ValueError
        self.assertEqual(result, (1000, 1024))
        mock_print.assert_any_call("❌ Invalid number entered. Using defaults.")

    @patch('builtins.print')
    @patch('builtins.input', side_effect=["2"])
    def test_select_profile_invalid_args_profile(self, mock_input, mock_print):
        """Test select_profile with an invalid args_profile falls back to input."""
        config_profiles = {
            "token_production": {"target_v": 20000, "res": 1024},
            "token_hobby": {"target_v": 10000, "res": 512}
        }

        # Calling with an invalid profile "invalid_profile"
        result = mp.select_profile(config_profiles, "invalid_profile")

        # It should print an error for the invalid profile
        mock_print.assert_any_call("❌ Error: Profile 'invalid_profile' not found in config.")

        # It should ask for input and we mocked it to return "2", which is "token_hobby"
        self.assertEqual(result, "token_hobby")
        mock_input.assert_called_once()

    def test_get_files_to_process_path_traversal(self):
        """Test process_file handles unwrapping and baking failure."""

        files = mp.get_files_to_process("single", "..\\..\\..\\Windows\\System32\\cmd.exe", "/source")
        self.assertEqual(files, ["cmd.exe.glb"])

        files = mp.get_files_to_process("single", "some\\path\\to\\file", "/source")
        self.assertEqual(files, ["file.glb"])

        files = mp.get_files_to_process("single", ".", "/source")
        self.assertEqual(files, [])

        files = mp.get_files_to_process("single", "..", "/source")
        self.assertEqual(files, [])

    @patch('builtins.input', return_value="")
    def test_get_files_to_process_single_empty_input(self, mock_input):
        """Test single mode handling empty filename prompt."""
        files = mp.get_files_to_process("single", "", "/source")
        self.assertEqual(files, [])
        mock_input.assert_called_once()

    def test_get_processing_mode_args_provided(self):
        """Test get_processing_mode when args.mode is provided."""
        self.assertEqual(mp.get_processing_mode("single"), "single")
        self.assertEqual(mp.get_processing_mode("batch"), "batch")
        self.assertEqual(mp.get_processing_mode("meshy"), "meshy")

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

        app_paths = MagicMock()
        app_paths.scripts = '/scripts'

        profile_data = {'norm': 1, 'matte': 1}

        mock_unwrap_and_bake.return_value = False

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
                import subprocess; raise subprocess.CalledProcessError(1, cmd, "Mock Instant Meshes Error")
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


class TestPipelineInitialization(unittest.TestCase):

    @patch('scripts.main_pipeline.parse_args')
    @patch('scripts.main_pipeline.get_app_paths')
    @patch('scripts.main_pipeline.load_config')
    @patch('scripts.main_pipeline.os.makedirs')
    @patch('scripts.main_pipeline.os.path.exists')
    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.shutil.which')
    def test_initialize_pipeline_success(self, mock_which, mock_subprocess_run, mock_exists, mock_makedirs, mock_load_config, mock_get_app_paths, mock_parse_args):
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
    @patch('scripts.main_pipeline.subprocess.run')
    @patch('scripts.main_pipeline.shutil.which')
    def test_initialize_pipeline_source_dir_failure(self, mock_which, mock_subprocess_run, mock_parse_args, mock_get_app_paths, mock_load_config, mock_exists, mock_makedirs):
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

    def test_resolve_path(self):
        """Test the resolve_path utility function."""
        root = "/base/dir" if os.name != 'nt' else "C:\\base\\dir"

        # Test absolute path
        abs_path = "/abs/path" if os.name != 'nt' else "C:\\abs\\path"
        self.assertEqual(mp.resolve_path(abs_path, root), abs_path)

        # Test relative path
        rel_path = "subdir/file.txt"
        expected = os.path.normpath(os.path.join(root, rel_path))
        self.assertEqual(mp.resolve_path(rel_path, root), expected)

        # Test path with ..
        rel_path_with_dots = "../outside/file.txt"
        expected = os.path.normpath(os.path.join(root, rel_path_with_dots))
        self.assertEqual(mp.resolve_path(rel_path_with_dots, root), expected)

        # Test current directory
        self.assertEqual(mp.resolve_path(".", root), os.path.normpath(root))

if __name__ == '__main__':
    unittest.main()
