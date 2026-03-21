import xml.etree.ElementTree as ET
import os

root = ET.Element("Settings")
root.set("Version", "3.19.3")
high_poly_model = ET.SubElement(root, "HighPolyModel")
high_mesh = ET.SubElement(high_poly_model, "Mesh")
high_mesh.set("File", os.path.normpath(os.path.abspath("test_high.obj")))
print(ET.tostring(root).decode())
