"""dcf"""
import os
import shutil

PROJECTS_DIRECTORY = "C:/Users/youmt/Programminng"

def remove_node_modules(directory):
    """shcdg"""
    patterns = [
        "node_modules",
        ".vscode-test",
        ".dart_tool",
        "build",
        "Generated.xcconfig",
        "flutter_export_environment.sh",
        "ephemeral",
        ".flutter-plugins-dependencies",
        ".flutter-plugins",
        ".gradle",
        ".yarn",
        ".angular",
    ]
    patternfiles = [
        "app-release.aab",
    ]
    for root, dirs, files in os.walk(directory):
        for pattern in patterns:
            if pattern in dirs:
                node_modules_path = os.path.join(root, pattern).replace("\\", "/")
                print(f"FOLDER {node_modules_path}")
                shutil.rmtree(node_modules_path)
        for pattern in patternfiles:
            if pattern in files:
                node_modules_path = os.path.join(root, pattern).replace("\\", "/")
                print(f"File {node_modules_path}")
                os.remove(node_modules_path)


# Call the function to remove node_modules folders
remove_node_modules(PROJECTS_DIRECTORY)
