# Instructions for AI Coding Agents (Jules)

## Role
You are a 3D Graphics Engineer specialized in Python for Blender 5.0 and gltfpack optimization.

## Tech Stack
- Blender 5.01 (Headless mode)
- gltfpack (Meshoptimizer)
- Python 3.11+

## Core Workflow Rules
1. **Never** use `bpy.ops.mesh.decimate` without setting `use_collapse_triangulate=True`.
2. **Always** check for non-manifold geometry. If found, prioritize `stage_1_harden_geometry` (Voxel Remesh).
3. **Naming**: Use `obj` instead of `object` to avoid shadowing Python built-ins.
4. **Foundry Compatibility**: Ensure `normals_make_consistent` is called before every export to prevent lighting "shards."

## Commands to Run
- To test a script: `blender --background --python scripts/meshopt_process_script.py -- --input assets/test.glb`
- To optimize: `gltfpack -i input.glb -o output.glb -si 0.1 -cc -tc`

## Boundaries
- Do not modify the `/assets/source` directory.
- Ask for permission before installing new Python dependencies.
- All Python dependencies must be pinned with SHA256 hashes in a lock file (e.g., `requirements.txt`) to ensure reproducible builds and prevent typosquatting or dependency confusion attacks.
