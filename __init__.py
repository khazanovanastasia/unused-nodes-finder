bl_info = {
    "name": "Unused Nodes Finder",
    "author": "khazanovanastasia",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Object > Unused Nodes Finder",
    "description": "Find and organize unused nodes in materials",
    "warning": "",
    "doc_url": "",
    "category": "Material",
}

import bpy
from . import main

def register():
    main.register()

def unregister():
    main.unregister()

if __name__ == "__main__":
    register()