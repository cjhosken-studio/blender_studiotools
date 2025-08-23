import bpy # type: ignore
from .. import utils

class STUDIOTOOLS_ANIMATION_Properties(bpy.types.PropertyGroup):

    export_path: bpy.props.StringProperty(
        name="Export Path",
        description="Export path",
        default="./",
        subtype="DIR_PATH"
    ) # type: ignore

    shot_name: bpy.props.StringProperty(
        name="Shot Name",
        description="",
        default="sh001"
    ) # type: ignore

classes = [STUDIOTOOLS_ANIMATION_Properties]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.studiotools_animation = bpy.props.PointerProperty(type=STUDIOTOOLS_ANIMATION_Properties)

def unregister():
    del bpy.types.Scene.studiotools_animation

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)