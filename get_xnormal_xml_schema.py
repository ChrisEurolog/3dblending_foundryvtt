import xml.etree.ElementTree as ET
import os

def create_xnormal_xml(high_poly_obj, low_poly_raw_obj, high_poly_tex, output_png, max_res):
    root = ET.Element("xNormal", version="3.19.3.39693")

    # The high poly model settings
    high_poly_model = ET.SubElement(root, "HighPolyModel")
    high_mesh = ET.SubElement(high_poly_model, "Mesh",
        file=high_poly_obj,
        scale="1.000000",
        ignorePerVertexColor="true")
    if high_poly_tex:
        high_mesh.set("baseTex", high_poly_tex)

    # The low poly model settings
    low_poly_model = ET.SubElement(root, "LowPolyModel")
    low_mesh = ET.SubElement(low_poly_model, "Mesh",
        file=low_poly_raw_obj,
        scale="1.000000",
        maxRayDistanceFront="0.050000",
        maxRayDistanceBack="0.050000")

    # Generate maps configuration
    generate_maps = ET.SubElement(root, "GenerateMaps",
        width=str(max_res),
        height=str(max_res),
        edgePadding="16",
        file=output_png,
        aa="4",
        genNormals="false",
        genAO="false",
        bakeHighpolyBaseTex="true")

    # xNormal requires an Options tag
    options = ET.SubElement(root, "Options", threadPriority="Normal", bucketSize="32")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    return ET.tostring(root).decode()

print(create_xnormal_xml("high.obj", "low.obj", "high.png", "out.png", 1024))
