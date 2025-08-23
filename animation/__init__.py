import bpy # type: ignore

from . import operators, ui, props

modules = [props, operators, ui]

def register():
    for mod in modules:
        mod.register()

def unregister():
    for mod in reversed(modules):
        mod.unregister()