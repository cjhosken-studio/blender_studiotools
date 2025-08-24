import os
import bpy # type: ignore
from .. import utils

class STUDIOTOOLS_ANIMATION_Properties(bpy.types.PropertyGroup):
    animation_name: bpy.props.StringProperty(
        name="Animation Name",
        default=os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(bpy.data.filepath))))
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