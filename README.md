# ChrisEurolog 3D Asset Pipeline for Foundry VTT

Automated processing scripts for converting Meshy AI outputs into production-ready 3D tokens for Pathfinder 2e and other Game Systems. This pipeline processes `.glb` files to merge geometry, decimate intelligently, apply matte finishes, and optimize for web performance.

## 🚀 Pipeline Features
- **Smart Decimation**: Balances high-fidelity visuals with VTT performance (Target: 20k-40k vertices).
- **Automated Mattening**: Reduces "greasy" look on Meshy assets by adjusting Coat and Subsurface weights.
- **Foundry Alignment**: Automatically snaps models to the floor and centers pivot points.
- **Meshopt Optimization**: Compresses assets for fast loading.
- **Dual Tracks**: Personal (Draco High-Poly) and Production (Meshopt Optimized).

## 🛠️ Setup & Requirements

1.  **Blender 5.0**: Ensure Blender is installed. Copy `axiom_config.json.template` to `axiom_config.json` and update the path if necessary.
2.  **gltfpack**: Download `gltfpack.exe` (from [meshoptimizer](https://github.com/zeux/meshoptimizer/releases)) and place it in the `tools/` folder (or update `axiom_config.json`).
3.  **Python 3.10+**: Required for running the scripts.

## ⚙️ Configuration

The pipeline is controlled by `axiom_config.json`. Start by copying `axiom_config.json.template` to `axiom_config.json`. You can customize:
-   **Paths**: Locations of executables and asset directories.
-   **Profiles**: Define target vertex counts and texture resolutions for different use cases (`token_production`, `token_hobby`, `tile`).

## 🏃 Usage

### Option 1: Running via Scripts (Recommended for Dev)
You can run the pipeline directly using the provided batch files:
-   **Double-click `run_single.bat`**: Process a single file interactively.
-   **Double-click `run_batch.bat`**: Process all `.glb` files in `assets/source/exports/`.

### Option 2: Building the Executable
To create a standalone `chriseurolog3d.exe` that you can share or move easily:

1.  Run `build_exe.bat`.
2.  This will install `pyinstaller` and compile the scripts.
3.  The output will be in the `dist/` folder:
    -   `dist/chriseurolog3d.exe`
    -   `dist/axiom_config.json`
4.  You can run `chriseurolog3d.exe` directly. Ensure `axiom_config.json` is in the same folder as the `.exe`.

## 📂 Directory Structure

```
chriseurolog3d/
├── assets/
│   ├── source/exports/  <-- Place raw .glb files here
│   ├── builds/          <-- Optimized files appear here
│   └── temp/            <-- Temporary working files
├── scripts/
│   ├── main_pipeline.py <-- Orchestrator
│   └── blender_worker.py <-- Blender script
├── tools/
│   └── gltfpack.exe     <-- Meshoptimizer tool
├── axiom_config.json    <-- Configuration
├── build_exe.bat        <-- Build script
├── run_single.bat       <-- Run script (Single Mode)
└── run_batch.bat        <-- Run script (Batch Mode)
```

## ⚖️ Licensing
This repository uses a **Hybrid Licensing** model to balance open-source collaboration with asset protection:

### 🛠️ The Code (Scripts & Batch Files)
All `.py` and `.bat` files in this repository are licensed under the **MIT License**. You are free to modify and use these scripts for your own pipelines.

### 🎨 The Assets (Models & Textures)
All 3D models (`.glb`, `.obj`), textures, and character designs (e.g., Anevia, Sossiel) are licensed under **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)**.
- **Attribution**: You must give credit to ChrisEurolog.
- **Non-Commercial**: You may not use these assets for commercial purposes or reselling.
- **Share-Alike**: If you remix these models, you must distribute them under the same license.

---
*Support the creation of more 3D tokens on patreon.com/chriseurolog.*
