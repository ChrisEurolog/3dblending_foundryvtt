import bpy
import bmesh
import math
import sys

def test():
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    # Split all edges to simulate unwelded FBX
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.edge_split()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Check vertex count
    print("Vertices before:", len(obj.data.vertices))

    # Weld
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    # Try different thresholds
    for thresh in [0.0000001, 0.0001, 0.001, 0.01]:
        res = bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=thresh)
        print(f"Removed with dist={thresh}:", len(res.get('rm_verts', [])) if isinstance(res, dict) else res)

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Vertices after:", len(obj.data.vertices))

test()
