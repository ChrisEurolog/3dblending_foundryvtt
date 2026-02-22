import os
import sys
import unittest
from unittest.mock import patch, MagicMock
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

if __name__ == '__main__':
    unittest.main()
