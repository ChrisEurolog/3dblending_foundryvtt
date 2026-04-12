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
        print(f"[{idx}] {name} ({details.get('target_v', 0)} verts, {details.get('res', 1024)}px)")

    while True:
        selection = input(f"Select Profile [1-{len(profile_options)}]: ").strip()
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(profile_options):
                return profile_options[idx][0]

        print("❌ Invalid selection. Please try again.")

def confirm_settings(profile_key, profile_data, auto=False):
    target_v = profile_data.get('target_v', 20000)
    max_res = profile_data.get('res', 1024)

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
            target_v = profile_data.get('target_v', 20000)
            max_res = profile_data.get('res', 1024)

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

def unwrap_and_bake(blender_exe, script_dir, f, high_poly_obj, low_poly_raw_obj, high_poly_tex, temp_base, temp_out_glb, max_res, target_v, profile_key):
    blender_unwrap = os.path.join(script_dir, "blender_unwrap_bake.py")

    profile_to_token_type = {
        "token_production": "1",
        "token_hobby": "2",
        "tile": "3",
        "archive": "4"
    }
    token_type = profile_to_token_type.get(profile_key, "1")

    # FIXED: Removed 'temp_base' from this list so it passes exactly 7 arguments
    unwrap_cmd = [
        blender_exe, "--background", "--python", blender_unwrap, "--",
        high_poly_obj, low_poly_raw_obj, high_poly_tex, temp_out_glb, str(max_res), str(target_v), token_type
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

    # Routing Paths
    temp_base = os.path.join(temp_dir, f.replace(".glb", ""))
    temp_out_glb = f"{temp_base}_unoptimized.glb"
    final_out = os.path.join(output_dir, f.replace(".glb", "_optimized.glb"))

    print(f"\n🔹 Processing: {f}")

    # 1. Blender Extraction Pass
    print("  Running Blender Extraction pass...")
    high_poly_obj = f"{temp_base}_high.obj"
    high_poly_tex = f"{temp_base}_high_diffuse.png"

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
    low_poly_raw_obj = f"{temp_base}_low_raw.obj"
    
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

        im_target = max(target_v, 100) 

        im_cmd = [
            instant_meshes_exe,
            "-o", low_poly_raw_obj,
            "-v", str(im_target),
            "-D",                 
            "-S", "0",            
            "-c", "30",           
            sculpt_obj_path
        ]

        try:
            subprocess.run(im_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Instant Meshes: {e}")
            return False

    # 3. Blender UV Unwrap and Bake Pass
    print("  Running Blender UV Unwrap and Bake pass...")
    bake_success = unwrap_and_bake(
        blender_exe, app_paths.scripts, f, high_poly_obj, low_poly_raw_obj, 
        high_poly_tex, temp_base, temp_out_glb, max_res, target_v, profile_key
    )
    
    if bake_success:
        # 4. GLTFPack Optimization Pass
        print("  Running Meshopt (gltfpack) pass...")
        if not os.path.exists(gltfpack_exe):
            print(f"⚠️ Warning: gltfpack not found at {gltfpack_exe}. Skipping compression.")
            shutil.copy(temp_out_glb, final_out)
        else:
            meshopt_cmd = [gltfpack_exe, "-i", temp_out_glb, "-o", final_out, "-noq"]
            try:
                subprocess.run(meshopt_cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"❌ Meshopt Error on {f}: {e}")
                return

        # 5. Archive and Cleanup
        print(f"✅ Success: {f} -> {final_out}")
        archive_dest = os.path.join(archive_dir, f)
        if os.path.exists(archive_dest):
            os.remove(archive_dest)
        shutil.move(input_path, archive_dest)

        # Optional: Clean up large temp GLB
        if os.path.exists(temp_out_glb):
            os.remove(temp_out_glb)

    else:
        print(f"❌ Failed during bake step: {f}")


# ==========================================
# MAIN EXECUTION LOOP
# ==========================================
def main():
    app_paths = get_app_paths()
    config = load_config(app_paths.base)
    
    if not config:
        print("Exiting due to missing configuration.")
        sys.exit(1)

    root_dir = app_paths.base
    paths = config['paths']

    root_dir = app_paths.base
    paths = config.get('paths', {})
    dirs = config.get('directories', {})

    # Extract executables from 'paths'
    blender_exe = resolve_path(paths.get('blender_exe', ''), root_dir)
    instant_meshes_exe = resolve_path(paths.get('instant_meshes_exe', ''), root_dir)
    xnormal_exe = resolve_path(paths.get('xnormal_exe', ''), root_dir)
    gltfpack_exe = resolve_path(paths.get('gltfpack_exe', ''), root_dir)
    
    # Extract folders from 'directories' (with safe fallbacks to prevent crashes)
    source_dir = resolve_path(dirs.get('source_files', paths.get('source_dir', './assets/source/exports')), root_dir)
    output_dir = resolve_path(dirs.get('output_tokens', paths.get('output_dir', './assets/builds')), root_dir)
    temp_dir = resolve_path(dirs.get('temp_processing', paths.get('temp_dir', './assets/temp')), root_dir)
    archive_dir = resolve_path(dirs.get('archive', paths.get('archive_dir', './assets/archive')), root_dir)

    # Ensure directories exist
    for d in [source_dir, output_dir, temp_dir, archive_dir]:
        os.makedirs(d, mode=0o755, exist_ok=True)

    # Setup Arguments and Profile
    args = parse_args()
    mode = get_processing_mode(args.mode)
    
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
