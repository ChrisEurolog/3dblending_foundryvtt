#!/bin/bash
export PATH="/usr/bin:$PATH"
if command -v blender &> /dev/null; then
    blender --background --python test_gltf.py
else
    echo "Blender not found"
fi
