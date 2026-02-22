import unittest
import sys
import os
import json
import struct
from unittest.mock import MagicMock

# Mock bpy before importing scripts.blender_worker
sys.modules['bpy'] = MagicMock()
sys.modules['bmesh'] = MagicMock()

import scripts.blender_worker as bw

class TestBlenderWorkerSecurity(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_security"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

    def tearDown(self):
        # Cleanup
        for root, dirs, files in os.walk(self.test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.test_dir)

    def create_gltf(self, filename, data):
        filepath = os.path.join(self.test_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f)
        return filepath

    def create_glb(self, filename, json_data):
        filepath = os.path.join(self.test_dir, filename)
        json_bytes = json.dumps(json_data).encode('utf-8')
        # Padding
        while len(json_bytes) % 4 != 0:
            json_bytes += b' '

        with open(filepath, 'wb') as f:
            # Header
            f.write(b'glTF')
            f.write(struct.pack('<I', 2)) # Version
            total_length = 12 + 8 + len(json_bytes)
            f.write(struct.pack('<I', total_length))

            # JSON Chunk
            f.write(struct.pack('<I', len(json_bytes)))
            f.write(b'JSON')
            f.write(json_bytes)
        return filepath

    def test_is_safe_uri(self):
        self.assertTrue(bw.is_safe_uri("data:image/png;base64,AAAA"))
        self.assertTrue(bw.is_safe_uri("texture.png"))
        self.assertTrue(bw.is_safe_uri("textures/diffuse.png"))

        # Test legitimate filenames with dots
        self.assertTrue(bw.is_safe_uri("my.model.v1.png"))
        self.assertTrue(bw.is_safe_uri("texture..diffuse.png"))

        self.assertFalse(bw.is_safe_uri("/etc/passwd"))
        self.assertFalse(bw.is_safe_uri("file:///etc/passwd"))
        self.assertFalse(bw.is_safe_uri("../secret.txt"))
        self.assertFalse(bw.is_safe_uri("textures/../../secret.txt"))
        self.assertFalse(bw.is_safe_uri("http://evil.com/exploit"))

        # Test URL encoded traversal
        self.assertFalse(bw.is_safe_uri("%2e%2e/passwd"))
        self.assertFalse(bw.is_safe_uri("textures/%2e%2e/secret.txt"))

        # Test absolute paths on Windows (mocked via logic)
        self.assertFalse(bw.is_safe_uri("C:/Windows/System32"))
        self.assertFalse(bw.is_safe_uri("C:\\Windows\\System32"))

        # Test backslashes
        self.assertFalse(bw.is_safe_uri("..\\secret.txt"))

    def test_validate_gltf_safe(self):
        data = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "data:application/octet-stream;base64,AA=="}]
        }
        filepath = self.create_gltf("safe.gltf", data)
        try:
            bw.validate_gltf_path(filepath)
        except ValueError as e:
            self.fail(f"validate_gltf_path raised ValueError unexpectedly: {e}")

    def test_validate_gltf_unsafe_buffer(self):
        data = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "/etc/passwd"}]
        }
        filepath = self.create_gltf("unsafe_buffer.gltf", data)
        with self.assertRaises(ValueError) as cm:
            bw.validate_gltf_path(filepath)
        self.assertIn("Unsafe buffer URI detected", str(cm.exception))

    def test_validate_gltf_unsafe_image(self):
        data = {
            "asset": {"version": "2.0"},
            "images": [{"uri": "../../../shadow"}]
        }
        filepath = self.create_gltf("unsafe_image.gltf", data)
        with self.assertRaises(ValueError) as cm:
            bw.validate_gltf_path(filepath)
        self.assertIn("Unsafe image URI detected", str(cm.exception))

    def test_validate_gltf_encoded_traversal(self):
        data = {
            "asset": {"version": "2.0"},
            "images": [{"uri": "%2e%2e/shadow"}]
        }
        filepath = self.create_gltf("unsafe_encoded.gltf", data)
        with self.assertRaises(ValueError) as cm:
            bw.validate_gltf_path(filepath)
        self.assertIn("Unsafe image URI detected", str(cm.exception))

    def test_validate_glb_safe(self):
        data = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "buffer.bin"}]
        }
        filepath = self.create_glb("safe.glb", data)
        try:
            bw.validate_gltf_path(filepath)
        except ValueError as e:
            self.fail(f"validate_gltf_path raised ValueError unexpectedly for GLB: {e}")

    def test_validate_glb_unsafe(self):
        data = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "/etc/shadow"}]
        }
        filepath = self.create_glb("unsafe.glb", data)
        with self.assertRaises(ValueError) as cm:
            bw.validate_gltf_path(filepath)
        self.assertIn("Unsafe buffer URI detected", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
