import bpy # type: ignore
from .. import utils as global_utils

class STUDIOTOOLS_ANIMATION_PT_AnimationPanel(bpy.types.Panel):
    """Creates a Panel in the 3D View sidebar"""
    bl_label = "Studio Tools Animation"
    bl_idname = "STUDIOTOOLS_ANIMATION_PT_AnimationPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Studio Tools Animation"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        pass

class STUDIOTOOLS_ANIMATION_PT_ExportPanel(bpy.types.Panel):
    bl_label = "Export"
    bl_parent_id = "STUDIOTOOLS_ANIMATION_PT_AnimationPanel"
    bl_idname = "STUDIOTOOLS_ANIMATION_PT_ExportPanel"
    bl_options = {'HIDE_HEADER'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout
        studiotools = context.scene.studiotools
        studiotools_animation = context.scene.studiotools_animation

        header = layout.label(text="Export")

        layout.prop(studiotools, "selected_collection", text="Root")
        row = layout.row()
        row.prop(studiotools_animation, "shot_name", text="Name")
        row.label(text=global_utils.get_current_version())

        layout.operator("studiotools_animation.export", text="Export Asset", icon='EXPORT')


classes = [STUDIOTOOLS_ANIMATION_PT_AnimationPanel, STUDIOTOOLS_ANIMATION_PT_ExportPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)