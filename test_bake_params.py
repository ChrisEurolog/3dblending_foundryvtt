with open('scripts/blender_worker.py', 'r') as f:
    content = f.read()

content = content.replace("bpy.context.scene.render.bake.margin = 8 # Prevent cross-island bleed overlap during baking\n        bpy.context.scene.render.bake.margin_type = 'EXTEND' # Prevent bleeding to black", "")
content = content.replace("bpy.context.scene.render.bake.margin = 8 # Prevent cross-island bleed overlap during baking", "")
content = content.replace("bpy.ops.object.bake(type='EMIT', use_selected_to_active=True)", "bpy.ops.object.bake(type='EMIT', use_selected_to_active=True, margin=8, margin_type='EXTEND')")

with open('scripts/blender_worker.py', 'w') as f:
    f.write(content)
