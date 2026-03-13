# Proposed Pipeline Architecture: Instant Meshes + PyMeshLab

## 1. Goal

Replace the unreliable, headless-hostile Blender Quad Remesher workflow with a robust, command-line driven pipeline for 3D token generation. The new pipeline will leverage Instant Meshes for quad topology generation and PyMeshLab (or similar headless tools) for UV unwrapping and texture baking.

## 2. Pipeline Stages

The new pipeline will consist of the following discrete stages, orchestrated by a central Python script (e.g., `scripts/main_pipeline.py`):

### Stage 1: Input Processing (Python)
*   **Input:** Meshy `.glb` file.
*   **Action:** Extract the high-poly mesh and texture (Albedo/Diffuse) from the `.glb`. This might require a lightweight extraction tool (like `trimesh` or a simple Blender script solely for export) to convert the `.glb` to `.obj` or `.ply` for Instant Meshes to consume, and save the texture image separately.
*   **Output:** High-poly `.obj` (or `.ply`) and `high_poly_texture.png`.

### Stage 2: Retopology (Instant Meshes CLI via `subprocess`)
*   **Input:** High-poly `.obj`.
*   **Tool:** Instant Meshes command-line interface.
*   **Action:** Execute Instant Meshes via `subprocess.run()`.
    *   Command example: `InstantMeshes -o low_poly_raw.obj -v 20000 high_poly.obj`
    *   Parameters: Adjust `-v` (vertex count) based on the profile target. Use `-d` (deterministic) if consistent output is required.
*   **Output:** Low-poly, quad-based `low_poly_raw.obj` (without UVs or textures).

### Stage 3: UV Unwrapping & Texture Baking (PyMeshLab / Headless Tool)
*   **Input:** High-poly `.obj`, `high_poly_texture.png`, Low-poly `low_poly_raw.obj`.
*   **Tool:** PyMeshLab (or xatlas for UVs + PyMeshLab/Blender for baking).

    **Option A: PyMeshLab only (if UV unwrapping is sufficient)**
    *   **Action:** Use PyMeshLab python API to:
        1. Load `low_poly_raw.obj`.
        2. Generate UV coordinates (e.g., `compute_texcoord_parametrization_triangle_trivial` or `compute_texcoord_by_isoparametrization`). *Note: PyMeshLab's automatic UV unwrapping can sometimes be rudimentary compared to Blender's Smart UV Project.*
        3. Load `high_poly.obj` and its texture.
        4. Transfer texture from high-poly to low-poly using a filter like `transfer_attributes_to_texture` or similar baking equivalent.
        5. Export the final textured `.obj` or `.ply`.

    **Option B: Hybrid xatlas (UV) + PyMeshLab/Blender (Bake)**
    *   *This is often more robust for UVs than pure PyMeshLab.*
    *   **Action 3.1 (UV Unwrapping):** Use the `xatlas` python binding to load `low_poly_raw.obj`, generate optimal UV islands with proper padding/margins, and save it as `low_poly_uv.obj`.
    *   **Action 3.2 (Texture Baking):** Use PyMeshLab (or a drastically simplified, non-remeshing headless Blender script) to project the high-poly texture onto `low_poly_uv.obj`.
        *   If using PyMeshLab for baking: Use `transfer_attributes_to_texture`.
        *   If using Blender for baking: A much simpler, faster headless Blender script that *only* imports the high/low objs, bakes the diffuse map, applies the matte finish, and exports the final `.glb`. This avoids the Quad Remesher instability entirely.

### Stage 4: Finalization & Export (Python / Meshopt)
*   **Input:** Textured low-poly mesh (e.g., `.obj` + `.png`).
*   **Action:** Convert the finalized model back to `.glb`. If using PyMeshLab, export to `.glb` (if supported in the specific version) or use a converter like `gltfpack`.
*   **Action:** Apply `gltfpack` (meshoptimizer) to compress the geometry and textures as currently done in the pipeline.
*   **Output:** Production-ready `final_optimized.glb`.

## 3. Recommended Approach

Given the requirements, the most stable path forward is a **Hybrid Approach**:

1.  **Extract:** Python script extracts `.obj` and texture from input `.glb`.
2.  **Retopologize:** `subprocess.run(['InstantMeshes', '-o', 'retopo.obj', '-v', str(target_verts), 'high.obj'])`.
3.  **UV Unwrap:** Use Python `xatlas` library to generate high-quality UVs with proper padding (`island_margin`).
4.  **Bake & Export:** A lightweight, headless Blender script (`blender_bake_only.py`). Since we removed the complex remeshing addons and GUI dependencies, this script will be incredibly fast and stable. It simply imports `high.obj`, imports `retopo_uv.obj`, bakes the texture, applies the matte material, and exports the final `.glb`.
5.  **Optimize:** `gltfpack`.

## 4. Next Steps for Implementation

1.  **Environment Setup:** Add `xatlas` and `pymeshlab` (if needed) to `requirements.txt`.
2.  **Instant Meshes Binary:** Determine how to package or reference the Instant Meshes executable (similar to how `gltfpack` is handled in `axiom_config.json`).
3.  **Refactor `main_pipeline.py`:** Update the pipeline orchestration to call these discrete stages instead of the single monolithic Blender worker.
4.  **Create Extraction/Baking Scripts:** Write the new Python and simplified Blender scripts.
