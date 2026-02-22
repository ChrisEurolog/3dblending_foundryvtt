import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock bpy and bmesh before importing the worker
mock_bpy = MagicMock()
mock_bmesh = MagicMock()

# We use patch.dict to safely insert mocks into sys.modules
sys.modules['bpy'] = mock_bpy
sys.modules['bmesh'] = mock_bmesh

import scripts.blender_worker as worker

class TestBlenderWorker(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test if needed
        mock_bpy.reset_mock()
        mock_bmesh.reset_mock()

    def test_missing_input_exits_with_error(self):
        """
        Verifies that the script exits with status code 1 when the input file is missing.
        """
        test_args = ['blender', '--background', '--python', 'script.py', '--', '--input', 'missing.glb', '--output', 'out.glb']

        with patch.object(sys, 'argv', test_args), \
             patch('os.path.exists', return_value=False), \
             patch('sys.exit') as mock_exit, \
             patch('builtins.print') as mock_print:

            worker.process()

            # Assert sys.exit was called with 1
            mock_exit.assert_called_with(1)

            # Verify error message
            printed_error = any("Error: Input file" in str(args[0]) for args, _ in mock_print.call_args_list if args)
            self.assertTrue(printed_error, "Error message should be printed")

if __name__ == '__main__':
    unittest.main()
