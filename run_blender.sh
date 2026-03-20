#!/bin/bash
export PATH="/mnt/c/Program Files/Blender Foundation/Blender 5.0/:$PATH"
if command -v blender &> /dev/null; then
    blender "$@"
else
    echo "Blender not found in path"
fi
