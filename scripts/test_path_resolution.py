import os
import sys
import unittest
from unittest.mock import patch

# Add scripts directory to path to import main_pipeline
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import main_pipeline

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

if __name__ == '__main__':
    unittest.main()
