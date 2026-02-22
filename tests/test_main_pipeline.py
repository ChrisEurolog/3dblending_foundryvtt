import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_frozen(self):
        # Case 1: Frozen with _MEIPASS
        fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))
        fake_meipass = '/tmp/_MEI12345'

        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys.executable = fake_exe
            mock_sys._MEIPASS = fake_meipass

            paths = mp.get_app_paths()
            self.assertEqual(paths.base, os.path.dirname(fake_exe))
            self.assertEqual(paths.scripts, fake_meipass)

    def test_get_app_paths_frozen_no_meipass(self):
        # Case 2: Frozen without _MEIPASS (fallback)
        fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))

        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys.executable = fake_exe
            del mock_sys._MEIPASS # Ensure it doesn't exist on the mock

            paths = mp.get_app_paths()
            self.assertEqual(paths.base, os.path.dirname(fake_exe))
            # Fallback is base_dir
            self.assertEqual(paths.scripts, os.path.dirname(fake_exe))

    def test_get_app_paths_not_frozen(self):
        # Case 3: Not frozen (dev mode)
        fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))

        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = False
            # We also need to patch __file__
            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()
                expected_scripts = os.path.dirname(fake_file)
                expected_base = os.path.abspath(os.path.join(expected_scripts, '..'))

                self.assertEqual(paths.scripts, expected_scripts)
                self.assertEqual(paths.base, expected_base)

if __name__ == '__main__':
    unittest.main()
