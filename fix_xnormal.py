import re

with open("scripts/blender_unwrap_bake.py", "r") as f:
    content = f.read()

# Replace xNormal XML generation logic
old_xml_logic = """        # Construct xNormal batch XML matching the schema provided by the user (v3.19.3)
        root = ET.Element("Settings")
        root.set("Version", "3.19.3")

        high_poly_model = ET.SubElement(root, "HighPolyModel")
        high_mesh = ET.SubElement(high_poly_model, "Mesh")
        high_mesh.set("File", os.path.normpath(os.path.abspath(high_poly_obj)))
        high_mesh.set("Scale", "1.000000")
        high_mesh.set("IgnorePerVertexColor", "true") # Force texture usage over vertex colors

        if high_poly_tex and os.path.exists(high_poly_tex):
            # Explicitly define the base texture on the Mesh tag
            high_mesh.set("BaseTex", os.path.normpath(os.path.abspath(high_poly_tex)))

        low_poly_model = ET.SubElement(root, "LowPolyModel")
        low_mesh = ET.SubElement(low_poly_model, "Mesh")
        low_mesh.set("File", os.path.normpath(os.path.abspath(temp_unwrapped_obj)))
        low_mesh.set("Scale", "1.000000")
        # Ensure Ray distance captures geometry just below or outside the surface
        low_mesh.set("MaxRayDistanceFront", "0.050000")
        low_mesh.set("MaxRayDistanceBack", "0.050000")

        # In the native Settings XML, the baking element is GenerateMaps
        generation = ET.SubElement(root, "GenerateMaps")
        generation.set("BakeHighpolyBaseTex", "true") # Bake Albedo/Diffuse
        generation.set("GenNormals", "false")
        generation.set("GenAO", "false")
        generation.set("Width", str(max_res))
        generation.set("Height", str(max_res))
        generation.set("EdgePadding", "16") # Increased to 16 to prevent bleeding/tearing around UV seams

        # Output file mapping: In xNormal batch configurations, the generic output path
        # for GenerateMaps is mapped via the File attribute. xNormal will use this prefix
        # and automatically append the generated map's suffix (e.g. _baseTex.png).
        generation.set("File", os.path.normpath(os.path.abspath(baked_tex_png)))

        # Ensure antialiasing is turned on for high quality
        generation.set("AA", "4")"""

new_xml_logic = """        # Construct xNormal batch XML matching xNormal 3.19.3 schema
        # Reference: xNormal requires exact casing and specific tags like <xNormal>, not <Settings>.
        root = ET.Element("xNormal")
        root.set("version", "3.19.3.39693")

        high_poly_model = ET.SubElement(root, "HighPolyModel")
        high_mesh = ET.SubElement(high_poly_model, "Mesh",
            file=os.path.normpath(os.path.abspath(high_poly_obj)),
            scale="1.000000",
            ignorePerVertexColor="true"
        )
        if high_poly_tex and os.path.exists(high_poly_tex):
            high_mesh.set("baseTex", os.path.normpath(os.path.abspath(high_poly_tex)))

        low_poly_model = ET.SubElement(root, "LowPolyModel")
        low_mesh = ET.SubElement(low_poly_model, "Mesh",
            file=os.path.normpath(os.path.abspath(temp_unwrapped_obj)),
            scale="1.000000",
            maxRayDistanceFront="0.050000",
            maxRayDistanceBack="0.050000",
            matchUv="true"
        )

        generation = ET.SubElement(root, "GenerateMaps",
            width=str(max_res),
            height=str(max_res),
            edgePadding="16",
            file=os.path.normpath(os.path.abspath(baked_tex_png)),
            aa="4",
            genNormals="false",
            genAO="false",
            bakeHighpolyBaseTex="true"
        )

        # Add Options block which xNormal batch processor expects
        options = ET.SubElement(root, "Options", threadPriority="Normal", bucketSize="32")"""

content = content.replace(old_xml_logic, new_xml_logic)

with open("scripts/blender_unwrap_bake.py", "w") as f:
    f.write(content)
