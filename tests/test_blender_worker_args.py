import unittest
from unittest.mock import MagicMock, patch
import sys
import argparse

# Mock bpy and bmesh before importing the worker
sys.modules['bpy'] = MagicMock()
sys.modules['bmesh'] = MagicMock()
sys.modules['addon_utils'] = MagicMock()

import scripts.blender_worker as worker

class TestBlenderWorkerArgs(unittest.TestCase):

    def test_build_args_returns_parser(self):
        """Verify that build_args() returns an argparse.ArgumentParser instance."""
        parser = worker.build_args()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_build_args_parsing_valid(self):
        """Verify correct parsing of valid argument lists."""
        parser = worker.build_args()
        args_list = [
            "--input", "in.glb",
            "--output", "out.glb",
            "--target", "10000",
            "--maxtex", "1024",
            "--normalize", "0",
            "--matte", "0"
        ]
        args = parser.parse_args(args_list)
        self.assertEqual(args.input, "in.glb")
        self.assertEqual(args.output, "out.glb")
        self.assertEqual(args.target, 10000)
        self.assertEqual(args.maxtex, 1024)
        self.assertEqual(args.normalize, 0)
        self.assertEqual(args.matte, 0)

    def test_build_args_defaults(self):
        """Verify the default values for optional arguments."""
        parser = worker.build_args()
        # Only required args
        args_list = ["--input", "in.glb", "--output", "out.glb"]
        args = parser.parse_args(args_list)
        self.assertEqual(args.target, 20000)
        self.assertEqual(args.maxtex, 2048)
        self.assertEqual(args.normalize, 1)
        self.assertEqual(args.matte, 1)

    def test_build_args_missing_required(self):
        """Verify that SystemExit is raised when required arguments are missing."""
        parser = worker.build_args()

        # Missing --output
        with patch('sys.stderr', new=MagicMock()): # Suppress stderr output
            with self.assertRaises(SystemExit):
                parser.parse_args(["--input", "in.glb"])

        # Missing --input
        with patch('sys.stderr', new=MagicMock()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--output", "out.glb"])

if __name__ == '__main__':
    unittest.main()
