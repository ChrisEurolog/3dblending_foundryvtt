import unittest
from unittest.mock import patch
import scripts.main_pipeline as mp

class TestMainPipelineSecurity(unittest.TestCase):

    def test_get_files_to_process_path_traversal_args(self):
        """Test that get_files_to_process strips directory paths from args.input."""
        # Setup
        mode = "single"
        # Simulate a path traversal attempt
        args_input = "../../etc/passwd"
        source_dir = "/tmp/source"

        # Execute
        files = mp.get_files_to_process(mode, args_input, source_dir)

        # Assert
        # Should be just the filename, with .glb appended if missing
        expected_filename = "passwd.glb"
        self.assertEqual(files, [expected_filename])

    def test_get_files_to_process_path_traversal_input(self):
        """Test that get_files_to_process strips directory paths from user input."""
        # Setup
        mode = "single"
        args_input = None
        source_dir = "/tmp/source"

        # Mock input() to return a path traversal attempt
        with patch('builtins.input', return_value="../../etc/shadow"):
            # Execute
            files = mp.get_files_to_process(mode, args_input, source_dir)

        # Assert
        expected_filename = "shadow.glb"
        self.assertEqual(files, [expected_filename])

    def test_get_files_to_process_absolute_path(self):
        """Test that get_files_to_process handles absolute paths correctly."""
        # Setup
        mode = "single"
        args_input = "/usr/local/bin/malicious"
        source_dir = "/tmp/source"

        # Execute
        files = mp.get_files_to_process(mode, args_input, source_dir)

        # Assert
        expected_filename = "malicious.glb"
        self.assertEqual(files, [expected_filename])

if __name__ == '__main__':
    unittest.main()
