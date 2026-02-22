import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import scripts.main_pipeline as mp

class TestResolvePath(unittest.TestCase):
    def test_absolute_path(self):
        """Should return the path as is if it's absolute."""
        abs_path = os.path.abspath("/tmp/file.txt")
        root_dir = "/home/user"
        resolved = mp.resolve_path(abs_path, root_dir)
        self.assertEqual(resolved, abs_path)

    def test_relative_path(self):
        """Should join root_dir and path if relative."""
        rel_path = "file.txt"
        root_dir = "/home/user"
        expected = os.path.join(root_dir, rel_path)
        resolved = mp.resolve_path(rel_path, root_dir)
        self.assertEqual(resolved, expected)

    def test_relative_path_with_backtracking(self):
        """Should normalize paths with backtracking (..)."""
        rel_path = "../file.txt"
        root_dir = "/home/user/project"
        expected = os.path.normpath(os.path.join(root_dir, rel_path))
        resolved = mp.resolve_path(rel_path, root_dir)
        self.assertEqual(resolved, expected)

class TestAppPaths(unittest.TestCase):
    def test_get_app_paths_frozen(self):
        """Should return correct paths when frozen (PyInstaller)."""
        fake_exe = "/path/to/exe"
        fake_meipass = "/tmp/_MEI12345"

        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', fake_exe), \
             patch.object(sys, '_MEIPASS', fake_meipass, create=True):

            paths = mp.get_app_paths()
            self.assertEqual(paths.base, os.path.dirname(fake_exe))
            self.assertEqual(paths.scripts, fake_meipass)

    def test_get_app_paths_dev(self):
        """Should return correct paths when running from source."""
        fake_file = "/home/user/project/scripts/main_pipeline.py"
        expected_script_dir = os.path.dirname(fake_file)
        expected_base_dir = os.path.abspath(os.path.join(expected_script_dir, '..'))

        # Patch sys.frozen to ensure it's False (or not set)
        # We need to ensure sys.frozen is False or doesn't exist.
        # Since we can't easily delete it if it exists inside a context manager without affecting global state,
        # we set it to False.
        with patch.object(sys, 'frozen', False, create=True), \
             patch('scripts.main_pipeline.__file__', fake_file):

            paths = mp.get_app_paths()
            self.assertEqual(paths.base, expected_base_dir)
            self.assertEqual(paths.scripts, expected_script_dir)

if __name__ == '__main__':
    unittest.main()
