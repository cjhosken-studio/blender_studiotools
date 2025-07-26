import bpy

def show_popup(title="Popup", text="", icon="INFO"):
    def draw(self, context):
        self.layout.label(text=text)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)
