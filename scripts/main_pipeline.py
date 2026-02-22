import os
import json
import subprocess
import shutil
import argparse
import tempfile
import sys
from collections import namedtuple

AppPaths = namedtuple('AppPaths', ['base', 'scripts'])

def get_app_paths():
    """
    Consolidated path resolution for frozen (PyInstaller) and dev environments.
    Returns a named tuple with 'base' and 'scripts' paths.
    """
    if getattr(sys, 'frozen', False):
        # In PyInstaller, bundled files are in sys._MEIPASS
        base_dir = os.path.dirname(sys.executable)
        script_dir = getattr(sys, '_MEIPASS', base_dir)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(script_dir, '..'))

    return AppPaths(base=base_dir, scripts=script_dir)

def load_config(base_dir):
    config_path = os.path.join(base_dir, 'axiom_config.json')
    config_path = os.path.normpath(config_path)

    if not os.path.exists(config_path):
        # Fallback: Check if config is bundled (e.g. for defaults)
        # But we prefer the one next to the exe.
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

    app_paths = get_app_paths()
    config = load_config(app_paths.base)
    if not config:
        # Prompt user to create one or exit?
        input("Press Enter to exit...")
        return

    root_dir = app_paths.base
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
        print("\nAvailable Profiles:")
        profile_options = list(config['profiles'].items())

        for idx, (name, details) in enumerate(profile_options, 1):
            print(f"[{idx}] {name} ({details['target_v']} verts, {details['res']}px)")

        while True:
            selection = input(f"Select Profile [1-{len(profile_options)}]: ").strip()
            if selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(profile_options):
                    profile_key = profile_options[idx][0]
                    break
            print("❌ Invalid selection. Please try again.")

    if profile_key not in config['profiles']:
        print(f"❌ Error: Invalid profile '{profile_key}'")
        return

    profile = config['profiles'][profile_key]

    # Override Vertex/Texture Prompts
    target_v = profile['target_v']
    max_res = profile['res']

    print(f"\n✅ Selected: {profile_key}")
    print(f"   Target Vertices: {target_v}")
    print(f"   Max Resolution: {max_res}px")

    override = input("\nPress Enter to use defaults, or type 'edit' to change values: ").strip().lower()
    if override == 'edit':
        try:
            v_input = input(f"Enter new Target Vertex Count (current: {target_v}): ").strip()
            if v_input:
                target_v = int(v_input)

            res_input = input(f"Enter new Max Texture Resolution (current: {max_res}): ").strip()
            if res_input:
                max_res = int(res_input)

            print(f"👉 New Settings: {target_v} verts, {max_res}px")
        except ValueError:
            print("❌ Invalid number entered. Using defaults.")
            target_v = profile['target_v']
            max_res = profile['res']

    # Determine Files
    files = []
    if mode == "single":
        filename = args.input
        if not filename:
             filename = input("\nFilename (in source/exports/): ").strip()

        # Security Fix: Prevent path traversal by ensuring only the filename is used
        filename = os.path.basename(filename)

        if not filename.endswith(".glb"):
            filename += ".glb"

        files = [filename]
    else:
        files = [f for f in os.listdir(source_dir) if f.endswith(".glb")]

    if not files:
        print("No files to process.")
        return

    print(f"\n🚀 Starting processing for {len(files)} files...")

    for f in files:
        input_path = os.path.join(source_dir, f)
        if not os.path.exists(input_path):
             print(f"⚠️ Warning: File not found: {input_path}")
             continue

        # Security Fix: Use a unique temporary directory to prevent symlink attacks
        file_temp_dir = tempfile.mkdtemp(dir=temp_dir)
        try:
            temp_out = os.path.join(file_temp_dir, f)
            final_out = os.path.join(output_dir, f.replace(".glb", "_optimized.glb"))

            print(f"🔹 Processing: {f}")

            # Blender Pass
            # Locate the bundled or relative blender_worker.py
            script_dir = app_paths.scripts
            blender_worker = os.path.join(script_dir, "blender_worker.py")

            if not os.path.exists(blender_worker):
                 # Try fallback: maybe we are running script directly but get_app_paths pointed somewhere else?
                 # But if is_frozen is false, app_paths.scripts points to script dir.
                 # If is_frozen is true, sys._MEIPASS (or base_dir) should have it.
                 print(f"❌ Error: blender_worker.py not found at {blender_worker}")
                 input("Press Enter to exit...")
                 return

            blender_cmd = [
                blender_exe, "--background", "--python", blender_worker, "--",
                "--input", input_path,
                "--output", temp_out,
                "--target", str(target_v),
                "--maxtex", str(max_res),
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
                    # Use safer compression for Foundry VTT
                    # -si: Simplification
                    # -noq: No Quantization (this is the key for compatibility)
                    # Removed -c and -cc which cause compression issues
                    meshopt_cmd = [meshopt_exe, "-si", "0.5", "-i", temp_out, "-o", final_out, "-noq"]
                    try:
                        subprocess.run(meshopt_cmd, check=True)
                    except subprocess.CalledProcessError as e:
                         print(f"❌ Meshopt Error on {f}: {e}")
                         continue
            else:
                shutil.copy(temp_out, final_out)

            print(f"✅ Success: {f} -> {final_out}")

        finally:
            # Cleanup secure temp dir
            shutil.rmtree(file_temp_dir, ignore_errors=True)

    print("Pipeline Finished.")

if __name__ == "__main__":
    run_pipeline()
