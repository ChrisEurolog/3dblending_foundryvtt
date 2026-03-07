import bpy
import os

# Create a sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
obj = bpy.context.active_object
mat = bpy.data.materials.new(name="TestMat")
mat.use_nodes = True
obj.data.materials.append(mat)

# Assign Principled BSDF with a specific color
nodes = mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")
bsdf.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['Roughness'].default_value = 0.8

# Try to export
bpy.ops.export_scene.gltf(
    filepath="test.glb",
    export_format='GLB',
    use_selection=True
)
print("Export complete")
