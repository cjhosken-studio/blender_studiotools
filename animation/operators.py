import bpy
import os
import re
from .. import io
from .. import utils as global_utils


class STUDIOTOOLS_ANIMATION_OT_Export(bpy.types.Operator):
    bl_idname = "studiotools_animation.export"
    bl_label = "Export Animation"
    bl_description = "Export Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        studiotools = context.scene.studiotools
        return studiotools.selected_collection

    def execute(self, context):
        studiotools = context.scene.studiotools
        studiotools_animation = context.scene.studiotools_animation

        blend_filepath = bpy.data.filepath

        if not blend_filepath:
            global_utils.save_version()
            
        version = global_utils.get_current_version()
        
        asset_folder = f"{studiotools_animation.animation_name}_v{version:03d}"
        filepath = os.path.abspath(os.path.join(studiotools_animation.export_path, asset_folder))

        success = io.export(filepath=filepath, root_collection=studiotools.selected_collection, export_animation=True)   
        if success:
            global_utils.show_popup("Export Complete!", f"Asset exported to {filepath}", "INFO")
            global_utils.save_version()

        return {'FINISHED'}
    
classes = [STUDIOTOOLS_ANIMATION_OT_Export]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)