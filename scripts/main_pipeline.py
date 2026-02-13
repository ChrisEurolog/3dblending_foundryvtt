import os
import json
import subprocess
import shutil
import argparse
import sys

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'axiom_config.json')
    config_path = os.path.normpath(config_path)

    if not os.path.exists(config_path):
        print(f"❌ Error: Config file not found at {config_path}")
        return None

    with open(config_path) as f:
        config = json.load(f)
    return config

def resolve_path(path, root_dir):
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(root_dir, path))

def run_pipeline():
    parser = argparse.ArgumentParser(description="ChrisEurolog 3D Asset Pipeline")
    parser.add_argument("--mode", choices=["single", "batch"], help="Processing mode")
    parser.add_argument("--profile", choices=["token_production", "token_hobby", "tile", "archive"], help="Optimization profile")
    parser.add_argument("--input", help="Input filename (for single mode)")
    args = parser.parse_args()

    config = load_config()
    if not config:
        return

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    paths = config['paths']

    # Resolve paths
    # Blender EXE might be system path or absolute.
    blender_exe = paths['blender_exe']
    meshopt_exe = resolve_path(paths['meshopt_exe'], root_dir)
    source_dir = resolve_path(paths['source_dir'], root_dir)
    output_dir = resolve_path(paths['output_dir'], root_dir)
    temp_dir = resolve_path(paths['temp_dir'], root_dir)

    # Ensure directories exist
    for d in [output_dir, temp_dir]:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(source_dir):
         # Create it if it doesn't exist? The instructions say "Source Acquisition... Place raw files in..."
         # But the pipeline reads from source/exports.
         # I'll create it to avoid immediate crashes if the user runs it on a fresh repo.
         try:
             os.makedirs(source_dir, exist_ok=True)
         except OSError:
             print(f"❌ Error: Source directory not found and could not be created: {source_dir}")
             return

    # Determine Mode
    mode = args.mode
    if not mode:
        print("--- chriseurolog3d Pipeline ---")
        mode_input = input("[1] Single [2] Batch: ").strip()
        mode = "single" if mode_input == "1" else "batch"

    # Determine Profile
    profile_key = args.profile
    if not profile_key:
        print("Available Profiles: " + ", ".join(config['profiles'].keys()))
        profile_key = input("Profile: ").strip()

    if profile_key not in config['profiles']:
        print(f"❌ Error: Invalid profile '{profile_key}'")
        return

    profile = config['profiles'][profile_key]

    # Determine Files
    files = []
    if mode == "single":
        filename = args.input
        if not filename:
             filename = input("Filename (in source/exports/): ").strip()

        if not filename.endswith(".glb"):
            filename += ".glb"

        files = [filename]
    else:
        files = [f for f in os.listdir(source_dir) if f.endswith(".glb")]

    if not files:
        print("No files to process.")
        return

    print(f"🚀 Starting processing for {len(files)} files with profile '{profile_key}'...")

    for f in files:
        input_path = os.path.join(source_dir, f)
        if not os.path.exists(input_path):
             print(f"⚠️ Warning: File not found: {input_path}")
             continue

        temp_out = os.path.join(temp_dir, f)
        final_out = os.path.join(output_dir, f.replace(".glb", "_optimized.glb"))

        print(f"🔹 Processing: {f}")

        # Blender Pass
        # We need to call blender_worker.py. It is in the same directory as this script.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        blender_worker = os.path.join(script_dir, "blender_worker.py")

        blender_cmd = [
            blender_exe, "--background", "--python", blender_worker, "--",
            "--input", input_path,
            "--output", temp_out,
            "--target", str(profile['target_v']),
            "--normalize", str(profile['norm']),
            "--matte", str(profile['matte'])
        ]

        print("  Running Blender pass...")
        try:
            subprocess.run(blender_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Blender Error on {f}: {e}")
            continue
        except FileNotFoundError:
            print(f"❌ Error: Blender executable not found at {blender_exe}")
            return

        # Meshopt Pass
        if profile_key != "archive":
            print("  Running Meshopt pass...")
            if not os.path.exists(meshopt_exe):
                 print(f"⚠️ Warning: gltfpack not found at {meshopt_exe}. Skipping optimization.")
                 shutil.copy(temp_out, final_out)
            else:
                meshopt_cmd = [meshopt_exe, "-si", "0.5", "-i", temp_out, "-o", final_out, "-cc"]
                try:
                    subprocess.run(meshopt_cmd, check=True)
                except subprocess.CalledProcessError as e:
                     print(f"❌ Meshopt Error on {f}: {e}")
                     continue
        else:
            shutil.copy(temp_out, final_out)

        # Cleanup
        if os.path.exists(temp_out):
            os.remove(temp_out)

        print(f"✅ Success: {f} -> {final_out}")

    print("Pipeline Finished.")

if __name__ == "__main__":
    run_pipeline()
