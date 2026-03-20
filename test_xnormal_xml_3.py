import xml.etree.ElementTree as ET
import sys

def build_xnormal_xml(high_obj, low_obj, high_tex, output_png, max_res):
    root = ET.Element("xNormal", version="3.19.3.39693")

    # HighPolyModel
    high_poly_model = ET.SubElement(root, "HighPolyModel")
    mesh_high = ET.SubElement(high_poly_model, "Mesh",
        scale="1.000000",
        file=high_obj,
        ignorePerVertexColor="true")
    if high_tex:
        mesh_high.set("baseTex", high_tex)

    # LowPolyModel
    low_poly_model = ET.SubElement(root, "LowPolyModel")
    mesh_low = ET.SubElement(low_poly_model, "Mesh",
        scale="1.000000",
        file=low_obj,
        maxRayDistanceFront="0.050000",
        maxRayDistanceBack="0.050000")

    # GenerateMaps
    generate_maps = ET.SubElement(root, "GenerateMaps",
        width=str(max_res),
        height=str(max_res),
        edgePadding="16",
        file=output_png,
        aa="4",
        genNormals="false",
        genAO="false",
        bakeHighpolyBaseTex="true"
    )

    # Options (sometimes required by xNormal)
    options = ET.SubElement(root, "Options",
        threadPriority="Normal",
        bucketSize="32")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    print(ET.tostring(root).decode())

build_xnormal_xml("C:\\temp\\high.obj", "C:\\temp\\low.obj", "C:\\temp\\diffuse.png", "C:\\temp\\out.png", 1024)
