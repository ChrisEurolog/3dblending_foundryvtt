import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import scripts.main_pipeline as mp

class TestMainPipeline(unittest.TestCase):

    def test_is_frozen_true(self):
        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = True
            self.assertTrue(mp.is_frozen())

    def test_is_frozen_false(self):
        with patch('scripts.main_pipeline.sys') as mock_sys:
            mock_sys.frozen = False
            self.assertFalse(mp.is_frozen())

    def test_is_frozen_missing(self):
        with patch('scripts.main_pipeline.sys') as mock_sys:
            if hasattr(mock_sys, 'frozen'):
                del mock_sys.frozen
            self.assertFalse(mp.is_frozen())

    def test_get_base_dir_not_frozen(self):
        with patch('scripts.main_pipeline.is_frozen', return_value=False):
            fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                base_dir = mp.get_base_dir()
                expected = os.path.abspath(os.path.join(os.path.dirname(fake_file), '..'))
                self.assertEqual(base_dir, expected)

    def test_get_base_dir_frozen(self):
        with patch('scripts.main_pipeline.is_frozen', return_value=True):
            fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))
            with patch('scripts.main_pipeline.sys') as mock_sys:
                mock_sys.executable = fake_exe
                base_dir = mp.get_base_dir()
                expected = os.path.dirname(fake_exe)
                self.assertEqual(base_dir, expected)

    def test_get_script_dir_not_frozen(self):
        with patch('scripts.main_pipeline.is_frozen', return_value=False):
            fake_file = os.path.abspath(os.path.join('scripts', 'main_pipeline.py'))
            with patch('scripts.main_pipeline.__file__', fake_file):
                script_dir = mp.get_script_dir()
                expected = os.path.dirname(fake_file)
                self.assertEqual(script_dir, expected)

    def test_get_script_dir_frozen_meipass(self):
        with patch('scripts.main_pipeline.is_frozen', return_value=True):
            fake_meipass = '/tmp/_MEI12345'
            with patch('scripts.main_pipeline.sys') as mock_sys:
                mock_sys._MEIPASS = fake_meipass
                script_dir = mp.get_script_dir()
                self.assertEqual(script_dir, fake_meipass)

    def test_get_script_dir_frozen_no_meipass(self):
        with patch('scripts.main_pipeline.is_frozen', return_value=True):
            fake_exe = os.path.abspath(os.path.join('path', 'to', 'exe'))
            with patch('scripts.main_pipeline.sys') as mock_sys:
                if hasattr(mock_sys, '_MEIPASS'):
                    del mock_sys._MEIPASS
                mock_sys.executable = fake_exe
                script_dir = mp.get_script_dir()
                expected = os.path.dirname(fake_exe)
                self.assertEqual(script_dir, expected)

if __name__ == '__main__':
    unittest.main()
