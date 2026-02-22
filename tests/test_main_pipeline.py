import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_frozen_with_meipass(self):
        # Simulate PyInstaller environment with _MEIPASS
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', '/path/to/exe'), \
             patch.object(sys, '_MEIPASS', '/tmp/_MEI12345', create=True):

            paths = mp.get_app_paths()
            self.assertEqual(paths.base, '/path/to')
            self.assertEqual(paths.scripts, '/tmp/_MEI12345')

    def test_get_app_paths_frozen_no_meipass(self):
        # Simulate PyInstaller environment without _MEIPASS (fallback to base)
        # We need to remove _MEIPASS if it exists
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', '/path/to/exe'):

            # Ensure _MEIPASS is not present
            if hasattr(sys, '_MEIPASS'):
                del sys._MEIPASS

            paths = mp.get_app_paths()
            self.assertEqual(paths.base, '/path/to')
            self.assertEqual(paths.scripts, '/path/to') # Fallback to base_dir

    def test_get_app_paths_not_frozen(self):
        # Simulate Dev environment
        # sys.frozen should be False or missing
        with patch.object(sys, 'frozen', False, create=True):
            fake_file = os.path.abspath(os.path.join('/fake/project/scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()
                expected_script_dir = os.path.dirname(fake_file)
                expected_base_dir = os.path.dirname(expected_script_dir)

                self.assertEqual(paths.scripts, expected_script_dir)
                self.assertEqual(paths.base, expected_base_dir)

if __name__ == '__main__':
    unittest.main()
