import unittest
import os
import json
import struct
from unittest.mock import patch, MagicMock

# Mock bpy before importing blender_extract
import sys
sys.modules['bpy'] = MagicMock()

import scripts.blender_extract as be

class TestBlenderExtractSecurity(unittest.TestCase):

    def test_is_safe_uri(self):
        # Safe URIs
        self.assertTrue(be.is_safe_uri("texture.png"))
        self.assertTrue(be.is_safe_uri("data:image/png;base64,iVBORw0KGgo"))
        self.assertTrue(be.is_safe_uri("textures/diffuse.jpg"))

        # Unsafe URIs
        self.assertFalse(be.is_safe_uri("file:///etc/passwd"))
        self.assertFalse(be.is_safe_uri("/absolute/path/image.png"))
        self.assertFalse(be.is_safe_uri("C:\\Windows\\System32\\cmd.exe"))
        self.assertFalse(be.is_safe_uri("../../../etc/shadow"))
        self.assertFalse(be.is_safe_uri("textures/../../secret.txt"))
        self.assertFalse(be.is_safe_uri("http://malicious.com/image.png"))

    def test_validate_gltf_path_safe_gltf(self):
        safe_gltf = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "buffer.bin"}],
            "images": [{"uri": "image.png"}]
        }

        with open("safe_test.gltf", "w") as f:
            json.dump(safe_gltf, f)

        try:
            self.assertTrue(be.validate_gltf_path("safe_test.gltf"))
        finally:
            os.remove("safe_test.gltf")

    def test_validate_gltf_path_unsafe_gltf(self):
        unsafe_gltf = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "buffer.bin"}],
            "images": [{"uri": "../../../etc/passwd"}]
        }

        with open("unsafe_test.gltf", "w") as f:
            json.dump(unsafe_gltf, f)

        try:
            with self.assertRaises(ValueError) as context:
                be.validate_gltf_path("unsafe_test.gltf")
            self.assertIn("Unsafe image URI detected", str(context.exception))
        finally:
            os.remove("unsafe_test.gltf")
