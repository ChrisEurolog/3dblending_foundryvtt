with open("scripts/blender_unwrap_bake.py", "r") as f:
    content = f.read()

import re

old_log = """        def print_xnormal_log():
            try:
                debug_log_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'xNormal', 'xNormal_debugLog.txt')
                if os.path.exists(debug_log_path):
                    with open(debug_log_path, 'r') as f:
                        print("\\n--- xNormal Debug Log ---")
                        lines = f.readlines()
                        print("".join(lines[-30:]))
                        print("-------------------------")
            except Exception:
                pass"""

new_log = """        def print_xnormal_log():
            try:
                # xNormal outputs its debug log to the user's Documents folder
                if 'USERPROFILE' in os.environ:
                    debug_log_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'xNormal', 'xNormal_debugLog.txt')
                    if os.path.exists(debug_log_path):
                        with open(debug_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            print("\\n--- xNormal Debug Log ---")
                            lines = f.readlines()
                            # Print the last 50 lines to ensure we catch the error reason
                            print("".join(lines[-50:]))
                            print("-------------------------")
                    else:
                        print(f"\\n--- No xNormal debug log found at {debug_log_path} ---")
            except Exception as ex:
                print(f"\\n--- Could not read xNormal debug log: {ex} ---")"""

content = content.replace(old_log, new_log)

old_fallback = """             # Fallback debug log parser
             try:
                 debug_log_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'xNormal', 'xNormal_debugLog.txt')
                 if os.path.exists(debug_log_path):
                     with open(debug_log_path, 'r') as f:
                         print("\\n--- xNormal Debug Log ---")
                         lines = f.readlines()
                         print("".join(lines[-20:]))
             except Exception:
                 pass"""

new_fallback = """             # Fallback debug log parser
             print_xnormal_log()"""

content = content.replace(old_fallback, new_fallback)

# Dump XML to log before execution so the user can debug XML issues directly
dump_xml_logic = """        # Execute xNormal
        # Note: xNormal CLI usually returns immediately while rendering in a background process,
        # but in batch mode it can be blocking depending on flags."""

new_dump_xml = """        print(f"🔹 xNormal Batch XML generated at: {xnormal_xml_path}")
        print("--- xNormal XML Configuration ---")
        try:
            with open(xnormal_xml_path, 'r') as xml_file:
                print(xml_file.read())
        except Exception:
            print("Could not read XML file to console.")
        print("---------------------------------")

        # Execute xNormal
        # Note: xNormal CLI usually returns immediately while rendering in a background process,
        # but in batch mode it can be blocking depending on flags."""

content = content.replace(dump_xml_logic, new_dump_xml)

with open("scripts/blender_unwrap_bake.py", "w") as f:
    f.write(content)
