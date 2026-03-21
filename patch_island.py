with open('scripts/blender_worker.py', 'r') as f:
    content = f.read()

content = content.replace("bpy.ops.uv.smart_project(angle_limit=1.55, margin_method='FRACTION', island_margin=0.01)", "bpy.ops.uv.smart_project(angle_limit=1.55, margin_method='FRACTION', island_margin=0.03)")

with open('scripts/blender_worker.py', 'w') as f:
    f.write(content)
