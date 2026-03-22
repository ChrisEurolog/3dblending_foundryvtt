import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)

# Create a cube at 1, 2, 3
bpy.ops.mesh.primitive_cube_add(location=(1, 2, 3))
bpy.ops.wm.obj_export(filepath='test1.obj')

# Clear
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import
bpy.ops.wm.obj_import(filepath='test1.obj')
imported_obj = bpy.context.selected_objects[0]
print("IMPORTED LOCATION:", imported_obj.location)
