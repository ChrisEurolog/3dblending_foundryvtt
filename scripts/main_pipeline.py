import os
import json
import subprocess
import shutil
import argparse
import sys
from collections import namedtuple

# Import pipeline steps directly instead of subprocesses for PyInstaller compatibility

AppPaths = namedtuple('AppPaths', ['base', 'scripts'])
PipelineConfig = namedtuple('PipelineConfig', [
    'args', 'app_paths', 'config', 'blender_exe', 'meshopt_exe',
    'source_dir', 'output_dir', 'temp_dir', 'instant_meshes_exe',
    'xnormal_exe', 'archive_dir'
])

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
        print(f"❌ Error: Config file not found at {config_path}")
        return None

    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        print("⚠️ Config not found. Using defaults.")
        return None
    except json.JSONDecodeError:
        print("❌ Error: Config file is not valid JSON.")
        return None

    if 'paths' in config:
        for key, path in config['paths'].items():
            if 'PATH_TO_' in path or 'YOUR_' in path:
                print(f"❌ Error: Configuration file '{config_path}' contains unconfigured placeholders (e.g., '{path}' for '{key}').")
                print("Please edit 'axiom_config.json' and provide actual paths to your tools and directories.")
                return None

    return config

def resolve_path(path, root_dir):
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(root_dir, path))

def parse_args():
    parser = argparse.ArgumentParser(description="ChrisEurolog 3D Asset Pipeline")
    parser.add_argument("--mode", choices=["single", "batch", "meshy"], help="Processing mode")
    parser.add_argument("--profile", choices=["token_production", "token_hobby", "tile", "archive"], help="Optimization profile")
    parser.add_argument("--input", help="Input filename (for single mode)")
    parser.add_argument("--auto", action="store_true", help="Run without interactive prompts")
    return parser.parse_args()

def get_processing_mode(args_mode):
    if args_mode:
        return args_mode
    print("--- chriseurolog3d Pipeline ---")
    mode_input = input("[1] Single [2] Batch [3] Meshy Generate: ").strip()
    if mode_input == "1": return "single"
    elif mode_input == "2": return "batch"
    elif mode_input == "3": return "meshy"
    return "single"

def select_profile(config_profiles, args_profile):
    if args_profile:
        if args_profile in config_profiles:
            return args_profile
        else:
            print(f"❌ Error: Profile '{args_profile}' not found in config.")

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

def confirm_settings(profile_key, profile_data, auto=False):
    target_v = profile_data['target_v']
    max_res = profile_data['res']

    print(f"\n✅ Selected: {profile_key}")
    print(f"   Target Vertices: {target_v}")
    print(f"   Max Resolution: {max_res}px")

    if auto:
        return target_v, max_res

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
             source_folder = os.path.basename(source_dir)
             filename = input(f"\nFilename (in {source_folder}/): ").strip()

        # Security Fix: Prevent path traversal by ensuring only the filename is used
        filename = filename.replace('\\', '/').split('/')[-1]

        if not filename or filename in (".", ".."):
            print(f"❌ Error: Invalid filename. Path traversal or empty input detected.")
            return []

        if not filename.endswith(".glb"):
            filename += ".glb"

        files = [filename]
    else:
        files = [f for f in os.listdir(source_dir) if f.endswith(".glb")]

    return files

def unwrap_and_bake(blender_exe, script_dir, f, high_poly_obj, low_poly_raw_obj, high_poly_tex, temp_out, max_res, target_v, profile_key):
    blender_unwrap = os.path.join(script_dir, "blender_unwrap_bake.py")

    token_type = "3" if profile_key == "tile" else "1"

    unwrap_cmd = [
        blender_exe, "--background", "--python", blender_unwrap, "--",
        high_poly_obj, low_poly_raw_obj, high_poly_tex, temp_out, str(max_res), str(target_v), token_type
    ]

    try:
        subprocess.run(unwrap_cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Blender UV/Bake Error on {f}: {e}")
        return False

def process_file(f, source_dir, temp_dir, output_dir, blender_exe, instant_meshes_exe, xnormal_exe, gltfpack_exe, profile_data, target_v, max_res, app_paths, profile_key, archive_dir):
    input_path = os.path.join(source_dir, f)
    if not os.path.exists(input_path):
            print(f"⚠️ Warning: File not found: {input_path}")
            return

    temp_out = os.path.join(temp_dir, f)
    final_out = os.path.join(output_dir, f.replace(".glb", "_optimized.glb"))

    print(f"🔹 Processing: {f}")

    # 1. Blender Extraction Pass
    print("  Running Blender Extraction pass...")
    high_poly_obj = os.path.join(temp_dir, f.replace(".glb", "_high.obj"))
    high_poly_tex = high_poly_obj.replace(".obj", "_diffuse.png")

    script_dir = app_paths.scripts
    blender_extract = os.path.join(script_dir, "blender_extract.py")

    extract_cap = profile_data.get('extract_v', target_v * 10)
    target_extract_v = str(extract_cap)

    extract_cmd = [
        blender_exe, "--background", "--python", blender_extract, "--",
        input_path, high_poly_obj, target_extract_v
    ]

    try:
        subprocess.run(extract_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Blender Extraction Error on {f}: {e}")
        return

    # 2. Instant Meshes Pass
    low_poly_raw_obj = os.path.join(temp_dir, f.replace(".glb", "_low_raw.obj"))
    
    if profile_key == "tile":
        print("  Skipping Instant Meshes pass for 'tile' profile...")
        with open(low_poly_raw_obj, 'w') as dummy:
            dummy.write("# Dummy file for tile profile\n")
    else:
        print("  Running Instant Meshes pass...")
        if not os.path.exists(instant_meshes_exe):
            print(f"❌ Error: Instant Meshes executable not found at {instant_meshes_exe}")
            raise FileNotFoundError(f"Instant Meshes executable not found at {instant_meshes_exe}")

        sculpt_obj_path = high_poly_obj.replace(".obj", "_sculpt.obj")
        if not os.path.exists(sculpt_obj_path):
            sculpt_obj_path = high_poly_obj

        # FIXED: Explicitly use the exact requested vertex count
        im_target = max(target_v, 100) 

        im_cmd = [
            instant_meshes_exe,
            "-o", low_poly_raw_obj,
            "-v", str(im_target), # FIXED: explicitly target vertices
            "-D",                 
            "-S", "0",            
            "-c", "30",           
            sculpt_obj_path
        ]

        try:
            subprocess.run(im_cmd, check=True)
            print("✅ Instant Meshes generated raw low poly model.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Instant Meshes: {e}")
            return False

    # 3. Blender UV Unwrap and Bake Pass
    print("  Running Blender UV Unwrap and Bake pass...")
    bake_success = unwrap_and_bake(
        blender_exe, app_paths.scripts, f, high_poly_obj, low_poly_raw_obj, 
        high_poly_tex, final_out, max_res, target_v, profile_key
    )
    
    if bake_success:
        print(f"✅ Successfully optimized and baked: {f}")
    else:
        print(f"❌ Failed during bake step: {f}")


# ==========================================
# MAIN EXECUTION LOOP (Restored)
# ==========================================
def main():
    app_paths = get_app_paths()
    config = load_config(app_paths.base)
    
    if not config:
        print("Exiting due to missing configuration.")
        sys.exit(1)

    # Extract paths from config
    blender_exe = resolve_path(config['paths']['blender_exe'], app_paths.base)
    instant_meshes_exe = resolve_path(config['paths']['instant_meshes_exe'], app_paths.base)
    xnormal_exe = resolve_path(config['paths'].get('xnormal_exe', ''), app_paths.base)
    gltfpack_exe = resolve_path(config['paths'].get('gltfpack_exe', ''), app_paths.base)
    
    source_dir = resolve_path(config['directories']['source_files'], app_paths.base)
    temp_dir = resolve_path(config['directories']['temp_processing'], app_paths.base)
    output_dir = resolve_path(config['directories']['output_tokens'], app_paths.base)
    archive_dir = resolve_path(config['directories'].get('archive', ''), app_paths.base)

    # Setup Arguments and Profile
    args = parse_args()
    mode = get_processing_mode(args.mode)
    
    # Optional handler for 'meshy' mode if needed in the future
    if mode == "meshy":
        print("Meshy generation selected. Implementation pending.")
        return

    profile_key = select_profile(config.get('profiles', {}), args.profile)
    profile_data = config['profiles'][profile_key]
    
    target_v, max_res = confirm_settings(profile_key, profile_data, args.auto)
    
    # Get files and process
    files = get_files_to_process(mode, args.input, source_dir)
    
    if not files:
        print("No files found to process.")
        return

    for f in files:
        process_file(
            f, source_dir, temp_dir, output_dir, blender_exe, 
            instant_meshes_exe, xnormal_exe, gltfpack_exe, 
            profile_data, target_v, max_res, app_paths, profile_key, archive_dir
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
        sys.exit(0)
