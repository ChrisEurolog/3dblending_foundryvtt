import sys
import unittest
from unittest.mock import MagicMock

# Mock bpy and bmesh before importing the module under test
sys.modules["bpy"] = MagicMock()
sys.modules["bmesh"] = MagicMock()

import scripts.blender_worker as bw

class TestBlenderWorker(unittest.TestCase):
    def test_build_args_defaults(self):
        """Test that default values are set correctly when only required arguments are provided."""
        parser = bw.build_args()
        args = parser.parse_args(["--input", "in.glb", "--output", "out.glb"])
        self.assertEqual(args.input, "in.glb")
        self.assertEqual(args.output, "out.glb")
        self.assertEqual(args.target, 40000)
        self.assertEqual(args.maxtex, 1024)
        self.assertEqual(args.normalize, 1)
        self.assertEqual(args.matte, 1)

    def test_build_args_custom(self):
        """Test that custom values are parsed correctly for all arguments."""
        parser = bw.build_args()
        args = parser.parse_args([
            "--input", "custom_in.glb",
            "--output", "custom_out.glb",
            "--target", "100",
            "--maxtex", "512",
            "--normalize", "0",
            "--matte", "0"
        ])
        self.assertEqual(args.input, "custom_in.glb")
        self.assertEqual(args.output, "custom_out.glb")
        self.assertEqual(args.target, 100)
        self.assertEqual(args.maxtex, 512)
        self.assertEqual(args.normalize, 0)
        self.assertEqual(args.matte, 0)

    def test_build_args_missing_required(self):
        """Test that argparse raises SystemExit when required arguments are missing."""
        parser = bw.build_args()
        # Redirect stderr to suppress argparse output during test
        with unittest.mock.patch('sys.stderr', new=unittest.mock.MagicMock()):
             with self.assertRaises(SystemExit):
                parser.parse_args(["--input", "in.glb"]) # Missing output

             with self.assertRaises(SystemExit):
                parser.parse_args(["--output", "out.glb"]) # Missing input

if __name__ == '__main__':
    unittest.main()
