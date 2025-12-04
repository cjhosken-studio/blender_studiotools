import bpy # type: ignore
from .. import utils as global_utils
import os

class STUDIOTOOLS_ASSET_PT_AssetPanel(bpy.types.Panel):
    """Creates a Panel in the 3D View sidebar"""
    bl_label = "Studio Tools Asset"
    bl_idname = "STUDIOTOOLS_ASSET_PT_AssetPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Studio Tools Asset"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Selection type
        layout.prop(scene.studiotools, "selection_type", expand=True)
        
        row = layout.row(align=True)
        # Show appropriate controls based on selection type
        if scene.studiotools.selection_type == "COLLECTION":
            row.prop(scene.studiotools, "selected_collection", text="")
        else:
            # For selected objects, you might want to show a list or count
            row.label(text=f"{len(context.selected_objects)} objects selected")

class STUDIOTOOLS_ASSET_PT_NamingPanel(bpy.types.Panel):
    """Creates a Panel in the 3D View sidebar"""
    bl_label = "Naming"
    bl_parent_id = "STUDIOTOOLS_ASSET_PT_AssetPanel"
    bl_idname = "STUDIOTOOLS_ASSET_PT_NamingPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        studiotools_asset = scene.studiotools_asset

        layout.label(text="Positional Prefix Naming")
        layout.prop(studiotools_asset, "name_pos_auto", text="Auto Detect")

        if (studiotools_asset.name_pos_auto):
            layout.prop(studiotools_asset, "name_pos_splitaxis", text="Split Axis")
            layout.prop(studiotools_asset, "name_pos_splittolerance", text="Tolerance")
        else:
            layout.prop(studiotools_asset, "name_pos", text="Prefix")

        layout.prop(studiotools_asset, "name_override", text="Override Names")
        label = "Objects" if scene.studiotools.selection_type == "OBJ" else "Collection"
        layout.operator("studiotools_asset.rename", icon='GREASEPENCIL', text=f"Rename {label}")

class STUDIOTOOLS_ASSET_UL_ShaderTagList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False)

        op = row.operator("studiotools_asset.shadertag_remove", text="", icon="X", emboss=False)
        op.index = index


class STUDIOTOOLS_ASSET_PT_ShaderPanel(bpy.types.Panel):
    """Creates a Panel in the 3D View sidebar"""
    bl_label = "Shader Tags"
    bl_parent_id = "STUDIOTOOLS_ASSET_PT_AssetPanel"
    bl_idname = "STUDIOTOOLS_ASSET_PT_ShaderPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout
        studiotools_asset = context.scene.studiotools_asset

        # Header with object name
        row = layout.row(align=True)
        row.prop(studiotools_asset, "shader_tag_name")

        # Management buttons
        row = layout.row(align=True)
        row.template_list(
            "STUDIOTOOLS_ASSET_UL_ShaderTagList",
            "",
            studiotools_asset,
            "shader_tags",
            studiotools_asset,
            "active_shader_tag_index",
            rows=4
        )
    
        col = row.column(align=True)
        col.operator("studiotools_asset.shadertag_add", text="", icon='ADD')
        col.operator("studiotools_asset.shadertag_refresh", text="", icon='FILE_REFRESH')
        
        layout.operator("studiotools_asset.shadertag_assign", text="Assign Tags", icon='FILE_REFRESH')

class STUDIOTOOLS_ASSET_PT_ExportPanel(bpy.types.Panel):
    bl_label = "Export"
    bl_parent_id = "STUDIOTOOLS_ASSET_PT_AssetPanel"
    bl_idname = "STUDIOTOOLS_ASSET_PT_ExportPanel"
    bl_options = {'HIDE_HEADER'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout
        studiotools = context.scene.studiotools
        studiotools_asset = context.scene.studiotools_asset
        
        layout.prop(studiotools, "selected_collection", text="Root")

        label = "Objects" if studiotools.selection_type == "OBJ" else "Collection"
        layout.prop(studiotools_asset, "asset_name", text="Name")

        if not os.environ["INPIPE"]:
            layout.prop(studiotools_asset, "export_path", text="Export Path")
        
        layout.operator("studiotools_asset.validate", text=f"Validate {label}", icon='FAKE_USER_ON')
        layout.operator("studiotools_asset.export", text="Export Asset", icon='EXPORT')


classes = [STUDIOTOOLS_ASSET_PT_AssetPanel, STUDIOTOOLS_ASSET_PT_NamingPanel, STUDIOTOOLS_ASSET_UL_ShaderTagList, STUDIOTOOLS_ASSET_PT_ShaderPanel, STUDIOTOOLS_ASSET_PT_ExportPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)