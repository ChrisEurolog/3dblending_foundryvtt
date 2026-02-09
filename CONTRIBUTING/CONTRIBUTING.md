# Contributing to 3D Pipeline

Thank you for helping build better Pathfinder 2e tokens! To ensure compatibility with Foundry VTT and the 3D Canvas module, please adhere to these standards:

## 📏 Technical Specifications
- **Scale**: 1 unit = 5 feet (Foundry standard).
- **Orientation**: +Y is Forward (South-facing by default in Foundry).
- **Format**: `.glb` only.
- **Polycount**: 
  - **Draco (Archive)**: ~150k - 500k triangles.
  - **Meshopt (Token)**: Target < 60k triangles for smooth VTT performance.

## 🎨 Asset Standards
- **Textures**: Exported at 1024px (tokens) or 2048px (bosses).
- **Topology**: Must be manifold (watertight). Use the "Voxel Remesh" step in the script if Meshy AI produces "thin shells" that shatter.
- **Naming**: Use `Snake_Case` (e.g., `Anevia_Tirabade_Token.glb`).

## 🛠️ Code Standards
- **Python**: Adhere to Blender 5.0+ API.
- **Modularity**: New logic must be added as a "Stage" in the `TokenProcessor` class.
