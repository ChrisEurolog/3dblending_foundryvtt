import os
import json
import subprocess
import shutil
import argparse
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

def parse_args():
    parser = argparse.ArgumentParser(description="ChrisEurolog 3D Asset Pipeline")
    parser.add_argument("--mode", choices=["single", "batch"], help="Processing mode")
    parser.add_argument("--profile", choices=["token_production", "token_hobby", "tile", "archive"], help="Optimization profile")
    parser.add_argument("--input", help="Input filename (for single mode)")
    return parser.parse_args()

def get_processing_mode(args_mode):
    if args_mode:
        return args_mode
    print("--- chriseurolog3d Pipeline ---")
    mode_input = input("[1] Single [2] Batch: ").strip()
    return "single" if mode_input == "1" else "batch"

def select_profile(config_profiles, args_profile):
    if args_profile:
        return args_profile

    print("\nAvailable Profiles:")
    profile_options = list(config_profiles.items())

    for idx, (name, details) in enumerate(profile_options, 1):
        print(f"[{idx}] {name} ({details['target_v']} verts, {details['res']}px)")

    while True:
        selection = input(f"Select Profile [1-{len(profile_options)}]: ").strip()
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(profile_options):
                return profile_options[idx][0]

        print("❌ Invalid selection. Please try again.")

def confirm_settings(profile_key, profile_data):
    target_v = profile_data['target_v']
    max_res = profile_data['res']

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
            target_v = profile_data['target_v']
            max_res = profile_data['res']

    return target_v, max_res

def get_files_to_process(mode, args_input, source_dir):
    files = []
    if mode == "single":
        filename = args_input
        if not filename:
             filename = input("\nFilename (in source/exports/): ").strip()

        # Security Fix: Prevent path traversal by ensuring only the filename is used
        filename = os.path.basename(filename)

        if not filename.endswith(".glb"):
            filename += ".glb"

        files = [filename]
    else:
        files = [f for f in os.listdir(source_dir) if f.endswith(".glb")]

    return files

def process_file(f, source_dir, temp_dir, output_dir, blender_exe, meshopt_exe, profile_data, target_v, max_res, app_paths, profile_key):
    input_path = os.path.join(source_dir, f)
    if not os.path.exists(input_path):
            print(f"⚠️ Warning: File not found: {input_path}")
            return

    temp_out = os.path.join(temp_dir, f)
    final_out = os.path.join(output_dir, f.replace(".glb", "_optimized.glb"))

    print(f"🔹 Processing: {f}")

    # Blender Pass
    # Locate the bundled or relative blender_worker.py
    script_dir = app_paths.scripts
    blender_worker = os.path.join(script_dir, "blender_worker.py")

    if not os.path.exists(blender_worker):
            print(f"❌ Error: blender_worker.py not found at {blender_worker}")
            raise FileNotFoundError(f"blender_worker.py not found at {blender_worker}")

    blender_cmd = [
        blender_exe, "--background", "--python", blender_worker, "--",
        "--input", input_path,
        "--output", temp_out,
        "--target", str(target_v),
        "--maxtex", str(max_res),
        "--normalize", str(profile_data['norm']),
        "--matte", str(profile_data['matte'])
    ]

    print("  Running Blender pass...")
    try:
        subprocess.run(blender_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Blender Error on {f}: {e}")
        return
    except FileNotFoundError:
        print(f"❌ Error: Blender executable not found at {blender_exe}")
        raise FileNotFoundError(f"Blender executable not found at {blender_exe}")

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
                    return
    else:
        shutil.copy(temp_out, final_out)

    # Cleanup
    if os.path.exists(temp_out):
        os.remove(temp_out)

    print(f"✅ Success: {f} -> {final_out}")

def run_pipeline():
    args = parse_args()

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
    mode = get_processing_mode(args.mode)

    # Determine Profile
    profile_key = select_profile(config['profiles'], args.profile)

    if profile_key not in config['profiles']:
        print(f"❌ Error: Invalid profile '{profile_key}'")
        return

    profile = config['profiles'][profile_key]

    # Override Vertex/Texture Prompts
    target_v, max_res = confirm_settings(profile_key, profile)

    # Determine Files
    files = get_files_to_process(mode, args.input, source_dir)

    if not files:
        print("No files to process.")
        return

    print(f"\n🚀 Starting processing for {len(files)} files...")

    for f in files:
        try:
            process_file(f, source_dir, temp_dir, output_dir, blender_exe, meshopt_exe, profile, target_v, max_res, app_paths, profile_key)
        except FileNotFoundError as e:
             # Critical error (e.g. executable not found), already printed in process_file
             input("Press Enter to exit...")
             return

    print("Pipeline Finished.")

if __name__ == "__main__":
    run_pipeline()
