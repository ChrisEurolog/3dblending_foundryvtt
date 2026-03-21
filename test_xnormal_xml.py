import xml.etree.ElementTree as ET
import os

root = ET.Element("Settings")
root.set("Version", "3.19.3.39693")
high_poly_model = ET.SubElement(root, "HighPolyModel")
high_mesh = ET.SubElement(high_poly_model, "Mesh")
high_mesh.set("File", "dummy.obj")
high_mesh.set("Scale", "1.000000")
high_mesh.set("IgnorePerVertexColor", "true")
high_mesh.set("BaseTexture", "dummy.png")
ET.dump(root)
