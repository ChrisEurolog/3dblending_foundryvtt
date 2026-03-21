with open("scripts/blender_unwrap_bake.py", "r") as f:
    content = f.read()

# check if Options got added
if "Add Options block" in content:
    print("Options block found")
else:
    print("Options block NOT found")
