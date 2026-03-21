import unittest
import os
from unittest.mock import patch
import scripts.main_pipeline as mp

class TestTraversalLogic(unittest.TestCase):
    def test_get_files_to_process_single_sanitization(self):
        source_dir = "/assets/source"

        test_cases = [
            ("normal.glb", "normal.glb"),
            ("subdir/normal.glb", "normal.glb"),
            ("../../../etc/passwd", "passwd.glb"),
            ("..\\..\\windows\\system32\\config", "config.glb"), # This is the one that might fail on POSIX
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                files = mp.get_files_to_process("single", input_val, source_dir)
                self.assertEqual(files[0], expected, f"Failed for input: {input_val}")

if __name__ == "__main__":
    unittest.main()
