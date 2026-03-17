import re

with open('scripts/bake_textures.py', 'r') as f:
    content = f.read()

# Replace any manual replacements with proper os.path.normpath to ensure Windows paths
# Also we will change <BaseTexture File="..."> to <BaseTex File="..."> or whatever xNormal uses. Actually, let's use both!
# xNormal v3 uses BaseTexture or Texture? Some people use <BaseTex> some <Texture>. Let's keep it <BaseTexture File="..."> since that's what the GUI produces usually, or we can use <Texture>.
# Wait, let's look at the XML exported from xNormal.
# <BaseTexture>C:\path.tga</BaseTexture> is sometimes used instead of File attribute.
# Let's set both attribute and text!
content = content.replace('high_mesh.set("File", os.path.abspath(high_poly_obj).replace("/", "\\\\"))', 'high_mesh.set("File", os.path.normpath(os.path.abspath(high_poly_obj)))')
content = content.replace('base_tex.set("File", os.path.abspath(high_poly_tex).replace("/", "\\\\"))', 'base_tex.set("File", os.path.normpath(os.path.abspath(high_poly_tex)))\n            base_tex.text = os.path.normpath(os.path.abspath(high_poly_tex))')
content = content.replace('low_mesh.set("File", os.path.abspath(temp_unwrapped_obj).replace("/", "\\\\"))', 'low_mesh.set("File", os.path.normpath(os.path.abspath(temp_unwrapped_obj)))')
content = content.replace('generation.set("File", os.path.abspath(baked_tex_png).replace("/", "\\\\"))', 'generation.set("File", os.path.normpath(os.path.abspath(baked_tex_png)))')

with open('scripts/bake_textures.py', 'w') as f:
    f.write(content)
