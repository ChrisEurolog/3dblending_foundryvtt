import os
import time
import base64
import requests
import subprocess
import sys

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
MESHY_API_KEY = os.environ.get('MESHY_API_KEY', 'YOUR_MESHY_KEY_HERE')
INPUT_FOLDER = './assets/portraits'

EXPORT_DIR = './assets/source/exports'

PIPELINE_SCRIPT = './scripts/main_pipeline.py'

TARGET_POLYCOUNT = 60000
TEXTURE_RES = "2048"

# ==========================================
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

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 202:
        return response.json()['result']
    print(f"❌ Error creating task: {response.text}")
    return None

def download_model(task_id, filename):
    url = f"https://api.meshy.ai/v1/image-to-3d/{task_id}"
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}

    print(f"⏳ Meshy is sculpting {filename}... (Usually 1-3 mins)")
    while True:
        response = requests.get(url, headers=headers)
        status = response.json().get('status')

        if status == 'SUCCEEDED':
            model_url = response.json()['model_urls']['glb']
            model_data = requests.get(model_url).content

            output_path = os.path.join(EXPORT_DIR, f"{os.path.splitext(filename)[0]}.glb")
            with open(output_path, 'wb') as f:
                f.write(model_data)

            print(f"✅ Downloaded to {output_path}")
            return True
        elif status == 'FAILED':
            print(f"❌ Meshy failed to process {filename}.")
            return False

        time.sleep(15)

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
                    os.rename(image_path, os.path.join(INPUT_FOLDER, f"{filename}.done"))

    if files_processed > 0:
        print(f"\n🚀 Generation complete. Handing off to ChrisEurolog Pipeline...")
        subprocess.run([
            sys.executable,
            PIPELINE_SCRIPT,
            "--mode", "batch",
            "--profile", "token_production"
        ], shell=False)
    else:
        print("\nNo new portraits found in ./assets/portraits/")

if __name__ == "__main__":
    main()
