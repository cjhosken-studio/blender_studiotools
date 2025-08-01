import bpy
from .operators import classes as op_classes

class STUDIOTOOLS_TOPBAR_MT_Menu(bpy.types.Menu):
    bl_label = "Studio Tools"
    bl_idname = "STUDIOTOOLS_TOPBAR_MT_Menu"

    def draw(self, context):
        layout = self.layout
        layout.separator()

        for cls in op_classes:
            layout.operator(cls.bl_idname, text=cls.bl_label)

def menu_draw(self, context):
    layout = self.layout
    layout.menu(STUDIOTOOLS_TOPBAR_MT_Menu.bl_idname)

classes = [STUDIOTOOLS_TOPBAR_MT_Menu]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_editor_menus.append(menu_draw)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_editor_menus.remove(menu_draw)