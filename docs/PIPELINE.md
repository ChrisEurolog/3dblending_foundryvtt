# 🎲 Foundry VTT Hybrid 3D Token Pipeline

This document outlines the end-to-end workflow for generating, cleaning, and optimizing 3D assets for Foundry VTT (3D Canvas). It utilizes a hybrid approach: AI for generation, Python scripting for automated mathematical cleanup, and minimal manual polish.

## 🗺️ Visual Workflow

```mermaid
flowchart TD
    subgraph Phase 0: Ideation & Prompting
        A[Concept Idea] --> B(Gemini Pro: Generate Optimized 3D-Ready Prompts)
    end

    subgraph Phase 1: 2D Generation DNA
        B --> C{What type of asset?}
        C -->|Safe Humanoid / Prop / Tile| D[Nano Banana / Midjourney]
        C -->|Monster / Non-Humanoid| E[Local ComfyUI + Depth/Canny ControlNet]
        C -->|NSFW / Edgy| F[Local ComfyUI Uncensored Checkpoints]
    end

    subgraph Phase 2: 3D Mesh Generation
        D --> G{Cloud Safe?}
        E --> H[Local Hunyuan3D Node]
        F --> H
        G -->|Yes| I[MeshyAI Cloud]
        G -->|No / Silhouette Focus| H
    end

    subgraph Phase 3: Texture Polish
        I --> J{Check Textures}
        H --> J
        J -->|Baked Lighting / Too Shiny| K[Unpack .glb -> Extract BaseColor.png]
        K --> L[Nano Banana / Qwen: Flatten & Remove Specular]
        L --> M[Repack to .glb]
        J -->|Clean & Flat| N[(Raw .glb Folder)]
        M --> N
    end

    subgraph Phase 4: Automated Optimization
        N --> O[Run: main_pipeline.py]
        O --> P[blender_worker.py executes]
        P --> Q[Merge Vertices: 0.0005]
        Q --> R[Decimate to Target Polycount]
        R --> S[Mattening Pass: Roughness 0.8]
        S --> T[Floor Alignment Z=0]
    end

    subgraph Phase 5: Final Human Polish
        T --> U[Open _optimized.glb in Blender]
        U --> V[Sculpt Mode: Lightly Smooth pinched vertices]
        V --> W(((Import to Foundry VTT)))
    end

🛠️ Phase Breakdown & Tool Integration
Phase 0: Prompt Creation (Gemini Pro)
Before generating any images, use Gemini Pro to construct the master prompt.

Input: Describe the character visually.

Output: Gemini provides a highly technical prompt tailored for 3D conversion (e.g., enforcing A-poses, flat lighting, orthographic framing, and negative prompts to eliminate dynamic shadows).

Phase 1: 2D Image Generation (The "DNA")
The goal is a clean, flat-lit, orthographic reference image.

Nano Banana: Best used for high-fidelity props, clean humanoid A-poses, and seamless environment tiles.

Local ComfyUI: Mandatory for edgy/NSFW content (to bypass cloud filters) and complex monsters (using ControlNet to anchor extra limbs).

Phase 2: 3D Generation
Converting the 2D silhouette into a .glb mesh.

MeshyAI: Excellent for standard assets and props.

Hunyuan3D (Local): Best for strict adherence to monster silhouettes and safely processing edgy content.

Phase 3: Texture Refinement (Nano Banana / Qwen)
If the 3D AI bakes shiny white highlights onto the skin or armor, unpack the .glb. Feed the BaseColor.png into Nano Banana or Qwen with the prompt: "Make lighting completely flat, remove all specular highlights, unify matte colors." Repack the texture.

Phase 4: Automated Optimization (Jules's Script)
Move the .glb files to the source_dir and run main_pipeline.py. The script will automatically scale the token, merge broken seams, reduce the polygon count, and apply a mathematical matte finish to the materials.

Phase 5: Manual Polish
Open the _optimized.glb in Blender. Switch to Sculpt Mode and use the Smooth Brush to quickly iron out any sharp, pinched vertices caused by the automated decimation. Export the final file and drop it into Foundry.
