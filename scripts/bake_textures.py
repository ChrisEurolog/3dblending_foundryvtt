import os

def unwrap_and_bake(high_obj, low_raw_obj, high_tex, output_glb, xnormal_exe, max_res=1024, target_v=20000):
    # 2. Baking with xNormal CLI
    print(f"🔹 Baking textures using xNormal...")
    if not os.path.exists(xnormal_exe):
        print(f"❌ Error: xNormal executable not found at {xnormal_exe}")
        return False

    return True
