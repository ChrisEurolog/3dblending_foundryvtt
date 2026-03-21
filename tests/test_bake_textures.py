import unittest
from unittest.mock import patch
import os

from scripts.bake_textures import unwrap_and_bake

class TestBakeTextures(unittest.TestCase):

    @patch('os.path.exists')
    @patch('builtins.print')
    def test_missing_xnormal_exe(self, mock_print, mock_exists):
        # Setup mock to return False for the xnormal_exe path
        mock_exists.return_value = False

        # Execute
        result = unwrap_and_bake('high.obj', 'low.obj', 'tex.png', 'out.glb', 'missing_xnormal.exe')

        # Assert
        self.assertFalse(result)
        mock_exists.assert_called_with('missing_xnormal.exe')

        # Verify the error message was printed
        error_printed = any("xNormal executable not found" in str(call_args) for call_args, _ in mock_print.call_args_list)
        self.assertTrue(error_printed)

if __name__ == '__main__':
    unittest.main()
