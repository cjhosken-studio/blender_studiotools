import bpy
from .. import utils


class STUDIOTOOLS_SHELF_SaveVersion(bpy.types.Operator):
    """Save and Version up the file"""
    bl_idname = "studiotools_shelf.save_version"
    bl_label = "Save Version"

    def execute(self, context):
        utils.save_version()
        return {"FINISHED"}
    
class STUDIOTOOLS_SHELF_OpenTools(bpy.types.Operator):
    bl_idname = "studiotools_shelf.open_tools"
    bl_label = "Open Tools"

    def execute(self, context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.show_region_ui = True

        return {"FINISHED"}

classes = [STUDIOTOOLS_SHELF_SaveVersion, STUDIOTOOLS_SHELF_OpenTools]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)