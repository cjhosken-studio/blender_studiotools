import bpy

class STUDIOTOOLS_IO_PT_ExportPanel(bpy.types.Panel):
    """Creates a Panel in the 3D View sidebar"""
    bl_label = "Export"
    bl_parent_id = "STUDIOTOOLS_PT_MainPanel"
    bl_idname = "STUDIOTOOLS_IO_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Tab"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.studiotools_io

        box = layout.box()
        box.label(text="Export", icon="EXPORT")
        box.prop(scene.studiotools, "selected_collection", text="Export Root")
        row = box.row()
        row.prop(props, "export_usd", toggle=True)
        row.prop(props, "export_blend", toggle=True)

        if props.export_usd:
            usd_box = box.box()
            usd_box.label(text="USD Options")

            col = usd_box.column()
            col.prop(props, "export_usd_type")
            col.prop(props, "export_usd_meshes")
            col.prop(props, "export_usd_lights")
            col.prop(props, "export_usd_cameras")
            col.prop(props, "export_usd_curves")
            col.prop(props, "export_usd_points")
            col.prop(props, "export_usd_volumes")
            col.separator()
            col.prop(props, "export_usd_rigs")
            col.prop(props, "export_usd_animation")
            col.separator()
            col.prop(props, "export_usd_materials")

            if (props.export_usd_materials):
                col.prop(props, "export_usd_materials_usd")
                col.prop(props, "export_usd_materials_mtlx")
                col.prop(props, "export_usd_textures_mode")
                col.prop(props, "export_usd_relative")

                if (props.export_use_textures_mode != "KEEP" and props.export_use_type == "USDZ"):
                    col.prop(props, "export_usd_textures_usdz_mode")

                    if (props.export_usd_textures_usdz_mode == "CUSTOM"):
                        col.prop(props, "export_usd_textures_usdz_size")

        box.prop(props, "export_version", text="Version")
        box.prop(props, "export_path", text="Path")
        layout.operator("studiotools_io.export")


class STUDIOTOOLS_IO_UL_ImportList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.label(text=item.name, icon='IMAGE_DATA' if item.type == 'TEX' else 'FILE_3D' if item.type == 'USD' else "FILE" if item.type == "CACHE" else "LINKED" if item.type == "LINK" else 'QUESTION')
            row.label(text=item.type)
            row.label(text=item.path)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='FILE')

class STUDIOTOOLS_IO_PT_ImportPanel(bpy.types.Panel):
    """Creates a Panel in the 3D View sidebar"""
    bl_label = "Import"
    bl_parent_id = "STUDIOTOOLS_PT_MainPanel"
    bl_idname = "STUDIOTOOLS_IO_PT_ImportPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Tab"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.studiotools_io
        
        box = layout.box()
        
        # List of import items
        row = box.row()
        row.template_list(
            "STUDIOTOOLS_IO_UL_ImportList", 
            "", 
            props, 
            "import_items", 
            props, 
            "active_item_index",
            rows=4
        )
        
        # Add/Remove buttons
        col = row.column(align=True)
        col.operator("studiotools_io.add_import_item", icon='ADD', text="")
        col.operator("studiotools_io.remove_import_item", icon='REMOVE', text="").index = props.active_item_index

classes = [STUDIOTOOLS_IO_PT_ExportPanel, STUDIOTOOLS_IO_UL_ImportList, STUDIOTOOLS_IO_PT_ImportPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)