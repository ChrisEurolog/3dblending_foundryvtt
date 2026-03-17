import bpy

def test():
    bake = bpy.context.scene.render.bake
    print("Bake attributes:")
    for attr in dir(bake):
        if not attr.startswith('_'):
            print(attr, getattr(bake, attr))

test()
