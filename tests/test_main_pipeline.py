import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_app_paths_frozen(self):
        # Case: sys.frozen is True
        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys.executable = '/path/to/exe'
            mock_sys._MEIPASS = '/tmp/_MEI12345'

            paths = mp.get_app_paths()

            self.assertEqual(paths.base, '/path/to')
            self.assertEqual(paths.scripts, '/tmp/_MEI12345')

    def test_get_app_paths_frozen_no_meipass(self):
        # Case: sys.frozen is True but _MEIPASS is missing (fallback)
        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            mock_sys.executable = '/path/to/exe'
            # Ensure _MEIPASS is not present on the mock
            del mock_sys._MEIPASS

            paths = mp.get_app_paths()

            self.assertEqual(paths.base, '/path/to')
            self.assertEqual(paths.scripts, '/path/to')

    def test_get_app_paths_not_frozen(self):
        # Case: sys.frozen is False or missing
        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = False

            fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                paths = mp.get_app_paths()

                expected_scripts = os.path.dirname(fake_file)
                expected_base = os.path.abspath(os.path.join(expected_scripts, '..'))

                self.assertEqual(paths.scripts, expected_scripts)
                self.assertEqual(paths.base, expected_base)

if __name__ == '__main__':
    unittest.main()
