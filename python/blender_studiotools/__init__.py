bl_info = {
    "name": "Blender Studio Tools",
    "author": "Christopher Hosken",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > StudioTools",
    "description": "",
    "warning": "",
    "wiki_url": "",
    "category": "3D View"
}

import bpy # type: ignore
from . import qt
from . import topmenu, asset, animation

modules = [topmenu, asset, animation]

class STUDIOTOOLS_Properties(bpy.types.PropertyGroup):
    selection_type: bpy.props.EnumProperty(
        name="Selection Type",
        description="",
        items = [
            ("COLLECTION", "Collection", "Process a specified collection's hierarchy"),
            ("OBJ", "Selected Objects", "Process selected objects")
        ],
        default="OBJ"
    ) # type: ignore

    selected_collection: bpy.props.PointerProperty(
        name="Collection",
        description="Collection to process",
        type=bpy.types.Collection
    ) # type: ignore

classes = [STUDIOTOOLS_Properties]

def register():
    qt.register()

    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.studiotools = bpy.props.PointerProperty(type=STUDIOTOOLS_Properties)

    for mod in modules:
        mod.register()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for mod in reversed(modules):
        mod.unregister()

    del bpy.types.Scene.studiotools

    qt.unregister()