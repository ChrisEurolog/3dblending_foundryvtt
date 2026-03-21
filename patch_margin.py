with open('scripts/blender_worker.py', 'r') as f:
    content = f.read()
content = content.replace("bpy.context.scene.render.bake.margin = 32 # Ensure healthy bleed margin for high-res before downscaling", "bpy.context.scene.render.bake.margin = 8 # Prevent cross-island bleed overlap during baking")
content = content.replace("bpy.ops.mesh.normals_make_consistent(inside=False) # Fix inside-out faces", "    # bpy.ops.mesh.normals_make_consistent(inside=False) # Omitted per user override to prevent lighting shards")
with open('scripts/blender_worker.py', 'w') as f:
    f.write(content)
