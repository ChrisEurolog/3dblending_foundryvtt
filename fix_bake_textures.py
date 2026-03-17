import re

with open('scripts/bake_textures.py', 'r') as f:
    content = f.read()

# Add kill xNormal logic before running it
kill_logic = """
        # Kill any existing xNormal processes to prevent hanging
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/IM', 'xNormal.exe'], capture_output=True, check=False)
        except Exception as e:
            pass

        # Execute xNormal
"""
content = content.replace("# Execute xNormal", kill_logic)

# Fix xNormal XML Base Texture mapping
# Some sources suggest xNormal 3 uses <BaseTex File="..."> or <BaseTexture File="...">
# And paths MUST be absolute Windows paths
xml_fix = """
        high_mesh.set("File", os.path.abspath(high_poly_obj).replace('/', '\\\\'))
        high_mesh.set("Scale", "1.000000")
        high_mesh.set("IgnorePerVertexColor", "true") # Force texture usage over vertex colors

        if high_poly_tex and os.path.exists(high_poly_tex):
            # Explicitly define the base texture
            base_tex = ET.SubElement(high_mesh, "BaseTexture")
            base_tex.set("File", os.path.abspath(high_poly_tex).replace('/', '\\\\'))
"""
content = re.sub(r'high_mesh\.set\("File", os\.path\.abspath\(high_poly_obj\)\).*?base_tex\.set\("File", os\.path\.abspath\(high_poly_tex\)\)', xml_fix, content, flags=re.DOTALL)

# Also fix the output file to use Windows path
content = content.replace('generation.set("File", os.path.abspath(baked_tex_png))', 'generation.set("File", os.path.abspath(baked_tex_png).replace("/", "\\\\"))')
content = content.replace('low_mesh.set("File", os.path.abspath(temp_unwrapped_obj))', 'low_mesh.set("File", os.path.abspath(temp_unwrapped_obj).replace("/", "\\\\"))')

with open('scripts/bake_textures.py', 'w') as f:
    f.write(content)
