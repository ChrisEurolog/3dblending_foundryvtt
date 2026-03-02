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

    def test_get_files_to_process_single_with_input(self):
        """Test single mode with provided filename and .glb extension."""
        files = mp.get_files_to_process("single", "test_file.glb", "/source")
        self.assertEqual(files, ["test_file.glb"])

    def test_get_files_to_process_single_with_input_no_ext(self):
        """Test single mode with provided filename lacking .glb extension."""
        files = mp.get_files_to_process("single", "test_file", "/source")
        self.assertEqual(files, ["test_file.glb"])

    @patch('builtins.input', return_value="prompted_file.glb")
    def test_get_files_to_process_single_prompt(self, mock_input):
        """Test single mode prompting for filename."""
        files = mp.get_files_to_process("single", None, "/source")
        self.assertEqual(files, ["prompted_file.glb"])
        mock_input.assert_called_once()

    def test_get_files_to_process_single_path_traversal(self):
        """Test single mode path traversal prevention."""
        files = mp.get_files_to_process("single", "../../../etc/passwd.glb", "/source")
        self.assertEqual(files, ["passwd.glb"])

        files = mp.get_files_to_process("single", "some/path/to/file", "/source")
        self.assertEqual(files, ["file.glb"])

    @patch('os.listdir')
    def test_get_files_to_process_batch(self, mock_listdir):
        """Test batch mode filtering for .glb files."""
        mock_listdir.return_value = ["file1.glb", "file2.txt", "file3.glb", "file4.GLB", "dir.glb/"]

        # It just uses endswith('.glb'), so "file4.GLB" won't be caught by endswith('.glb')
        # And "dir.glb/" won't be caught. "file1.glb", "file3.glb" will be caught.
        files = mp.get_files_to_process("batch", None, "/source")

        self.assertEqual(files, ["file1.glb", "file3.glb"])
        mock_listdir.assert_called_once_with("/source")


if __name__ == '__main__':
    unittest.main()
