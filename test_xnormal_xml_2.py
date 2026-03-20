import xml.etree.ElementTree as ET
import os

root = ET.Element("Settings")
root.set("Version", "3.19.3")

high_poly_model = ET.SubElement(root, "HighPolyModel")
high_mesh = ET.SubElement(high_poly_model, "Mesh")
high_mesh.set("File", "test_high.obj")
high_mesh.set("Scale", "1.000000")
high_mesh.set("IgnorePerVertexColor", "true")

low_poly_model = ET.SubElement(root, "LowPolyModel")
low_mesh = ET.SubElement(low_poly_model, "Mesh")
low_mesh.set("File", "test_low.obj")
low_mesh.set("Scale", "1.000000")
low_mesh.set("MaxRayDistanceFront", "0.050000")
low_mesh.set("MaxRayDistanceBack", "0.050000")

generation = ET.SubElement(root, "GenerateMaps")
generation.set("BakeHighpolyBaseTex", "true")
generation.set("GenNormals", "false")
generation.set("GenAO", "false")
generation.set("Width", "1024")
generation.set("Height", "1024")
generation.set("EdgePadding", "16")
generation.set("File", "test_out.png")
generation.set("AA", "4")

tree = ET.ElementTree(root)
ET.indent(tree, space="  ", level=0)
print(ET.tostring(root).decode())
