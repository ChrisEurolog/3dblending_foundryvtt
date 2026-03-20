import os
import time
import base64
import requests
import subprocess
import sys
import urllib.parse
from scripts.main_pipeline import get_app_paths, load_config, resolve_path

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
app_paths = get_app_paths()
config = load_config(app_paths.base) or {}
MESHY_API_KEY = config.get('meshy_api_key', os.environ.get('MESHY_API_KEY', 'YOUR_MESHY_KEY_HERE'))

INPUT_FOLDER = './assets/portraits'

# Use the resolved source directory from the main config so models end up in the right place
EXPORT_DIR = resolve_path(config.get('paths', {}).get('source_dir', './assets/source/exports'), app_paths.base)

PIPELINE_SCRIPT = './scripts/main_pipeline.py'

TARGET_POLYCOUNT = 60000
TEXTURE_RES = "2048"

# Security: Timeouts and retry limits for API and file downloads to prevent hanging
API_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120
MAX_RETRIES = 40  # 10 minutes (40 * 15s)
def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    extension = os.path.splitext(image_path)[1][1:].lower()
    if extension == 'jpg': extension = 'jpeg'
    return f"data:image/{extension};base64,{encoded_string}"

def create_meshy_task(image_data_uri):
    url = "https://api.meshy.ai/v1/image-to-3d"
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    payload = {
        "image_url": image_data_uri,
        "enable_pbr": True,
        "target_polycount": TARGET_POLYCOUNT,
        "texture_res": TEXTURE_RES,
        "topology": "quad"  # Quads for smooth Blender decimation!
    }

    response = requests.post(url, headers=headers, json=payload, timeout=API_TIMEOUT)
    if response.status_code == 202:
        return response.json()['result']
    print(f"❌ Error creating task: {response.text}")
    return None

def download_model(task_id, filename):
    url = f"https://api.meshy.ai/v1/image-to-3d/{task_id}"
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}

    print(f"⏳ Meshy is sculpting {filename}... (Usually 1-3 mins)")
    retries = 0
    while retries < MAX_RETRIES:
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        retries += 1
        status = response.json().get('status')

        if status == 'SUCCEEDED':
            model_url = response.json()['model_urls']['glb']

            parsed_url = urllib.parse.urlparse(model_url)
            if parsed_url.scheme != 'https':
                print(f"❌ Security Error: Invalid URL scheme '{parsed_url.scheme}'. Expected 'https'.")
                return False

            if not parsed_url.hostname.endswith('.meshy.ai') and parsed_url.hostname != 'meshy.ai':
                print(f"❌ Security Error: Invalid URL host '{parsed_url.hostname}'.")
                return False

            model_data = requests.get(model_url, timeout=DOWNLOAD_TIMEOUT).content

            output_path = os.path.join(EXPORT_DIR, f"{os.path.splitext(filename)[0]}.glb")
            with open(output_path, 'wb') as f:
                f.write(model_data)

            print(f"✅ Downloaded to {output_path}")
            return True
        elif status == 'FAILED':
            print(f"❌ Meshy failed to process {filename}.")
            return False

        time.sleep(15)

    print(f"❌ Timed out waiting for {filename} after {MAX_RETRIES} attempts.")
    return False

def main():
    os.makedirs(INPUT_FOLDER, mode=0o755, exist_ok=True)
    os.makedirs(EXPORT_DIR, mode=0o755, exist_ok=True)

    files_processed = 0
    if os.path.exists(INPUT_FOLDER):
        for filename in os.listdir(INPUT_FOLDER):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                print(f"\n--- Initiating Meshy generation for {filename} ---")
                image_path = os.path.join(INPUT_FOLDER, filename)

                data_uri = get_base64_image(image_path)
                task_id = create_meshy_task(data_uri)

                if task_id and download_model(task_id, filename):
                    files_processed += 1
                    os.remove(image_path)
                    print(f"🗑️ Removed original image: {filename}")

    if files_processed > 0:
        print(f"\n🚀 Generation complete. Handing off to ChrisEurolog Pipeline...")

        # Check if running as PyInstaller executable
        if getattr(sys, 'frozen', False):
            # In compiled exe, sys.executable IS the pipeline script
            cmd = [
                sys.executable,
                "--mode", "batch",
                "--profile", "token_production",
                "--auto"
            ]
        else:
            cmd = [
                sys.executable,
                PIPELINE_SCRIPT,
                "--mode", "batch",
                "--profile", "token_production",
                "--auto"
            ]

        subprocess.run(cmd, shell=False)
    else:
        print("\nNo new portraits found in ./assets/portraits/")

if __name__ == "__main__":
    main()
