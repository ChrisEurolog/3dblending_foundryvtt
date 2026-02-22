import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_get_base_dir_not_frozen(self):
        with patch.object(sys, 'frozen', False, create=True):
            fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                base_dir = mp.get_app_paths().base
                expected = os.path.abspath(os.path.join(os.path.dirname(fake_file), '..'))
                self.assertEqual(base_dir, expected)

    def test_get_base_dir_frozen(self):
        with patch.object(sys, 'frozen', True, create=True):
            fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))
            with patch.object(sys, 'executable', fake_exe):
                base_dir = mp.get_app_paths().base
                expected = os.path.dirname(fake_exe)
                self.assertEqual(base_dir, expected)

    def test_get_script_dir_not_frozen(self):
        with patch.object(sys, 'frozen', False, create=True):
            fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                script_dir = mp.get_app_paths().scripts
                expected = os.path.dirname(fake_file)
                self.assertEqual(script_dir, expected)

    def test_get_script_dir_frozen_meipass(self):
        with patch.object(sys, 'frozen', True, create=True):
            fake_meipass = '/tmp/_MEI12345'
            with patch.object(sys, '_MEIPASS', fake_meipass, create=True):
                with patch.object(sys, 'executable', '/path/to/exe'):
                    script_dir = mp.get_app_paths().scripts
                    self.assertEqual(script_dir, fake_meipass)

    def test_get_script_dir_frozen_no_meipass(self):
        with patch.object(sys, 'frozen', True, create=True):
            fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))
            # Ensure _MEIPASS is not present
            with patch.dict(sys.__dict__):
                if hasattr(sys, '_MEIPASS'):
                    del sys._MEIPASS

                with patch.object(sys, 'executable', fake_exe):
                    script_dir = mp.get_app_paths().scripts
                    # Logic: script_dir = getattr(sys, '_MEIPASS', base_dir)
                    # base_dir = dirname(executable)
                    expected = os.path.dirname(fake_exe)
                    self.assertEqual(script_dir, expected)

if __name__ == '__main__':
    unittest.main()
