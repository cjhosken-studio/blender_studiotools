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

import bpy

from . import io, asset

modules = [io, asset]

class STUDIOTOOLS_Properties(bpy.types.PropertyGroup):
    selection_type: bpy.props.EnumProperty(
        name="Selection Type",
        description="",
        items = [
            ("COLLECTION", "Collection", "Process a specified collection's hierarchy"),
            ("OBJ", "Selected Objects", "Process selected objects")
        ],
        default="OBJ"
    )

    selected_collection: bpy.props.PointerProperty(
        name="Collection",
        description="Collection to process",
        type=bpy.types.Collection
    )


class STUDIOTOOLS_PT_MainPanel(bpy.types.Panel):
    bl_label = "Studio Tools"
    bl_idname = "STUDIOTOOLS_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.studiotools
        
        # Selection type
        layout.prop(props, "selection_type", expand=True)
        
        # Show appropriate controls based on selection type
        if props.selection_type == "COLLECTION":
            row = layout.row()
            row.prop(props, "selected_collection", text="")
        else:
            # For selected objects, you might want to show a list or count
            layout.label(text=f"{len(context.selected_objects)} objects selected")
    

classes = [STUDIOTOOLS_Properties, STUDIOTOOLS_PT_MainPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.studiotools = bpy.props.PointerProperty(type=STUDIOTOOLS_Properties)

    for mod in modules:
        mod.register()

def unregister():
    for mod in reversed(modules):
        mod.unregister()

    del bpy.types.Scene.studiotools

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

try:
    unregister()
except:
    pass

register()