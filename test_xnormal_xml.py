import xml.etree.ElementTree as ET

root = ET.Element("xNormal")
high = ET.SubElement(root, "HighPolyModel")
mesh = ET.SubElement(high, "Mesh", Scale="1.0", File="path/to/high.obj", IgnorePerVertexColor="true")
tex = ET.SubElement(mesh, "BaseTexture", File="path/to/tex.png")
tree = ET.ElementTree(root)
ET.indent(tree)
print(ET.tostring(root, encoding="unicode"))
