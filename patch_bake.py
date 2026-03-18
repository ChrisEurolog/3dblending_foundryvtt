import re

with open('scripts/blender_worker.py', 'r') as f:
    content = f.read()

# Replace the margin setting
content = content.replace("bpy.context.scene.render.bake.margin = 8 # Prevent cross-island bleed overlap during baking", "bpy.context.scene.render.bake.margin = 8 # Prevent cross-island bleed overlap during baking\n        bpy.context.scene.render.bake.margin_type = 'EXTEND' # Prevent bleeding to black")

# Make sure we don't accidentally do it twice
with open('scripts/blender_worker.py', 'w') as f:
    f.write(content)
