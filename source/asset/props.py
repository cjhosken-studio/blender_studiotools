import bpy
from .. import utils

class STUDIOTOOLS_ASSET_ShaderTag(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Tag Name",
        default="default",
        update=lambda self, context: self._on_name_update(context)
    )

    last: bpy.props.StringProperty(
        name="",
        default=""
    )
    
    def _on_name_update(self, context):
        """Handle tag name changes and update associated materials and objects"""
        # Get all existing names except our own
        existing_names = [tag.name for tag in context.scene.studiotools_asset.shader_tags 
                        if tag != self]
        
        if self.name in existing_names:
            self.name = self.last
            return
        
        
        
        # Store previous name before updating
        old_material_name = f"{self.last}_SHD"
        new_material_name = f"{self.name}_SHD"
        
        # Update material if it exists
        material = None
        if old_material_name in bpy.data.materials:
            material = bpy.data.materials[old_material_name]
            if new_material_name not in bpy.data.materials:
                material.name = new_material_name
            else:
                print(f"Warning: Material {new_material_name} already exists")
        
        # Update objects with this tag
        for obj in bpy.data.objects:
            if not utils.check_primvar(obj, "shaderTag"):
                continue
                
            current_tag = obj["shaderTag"]
            if current_tag == self.last:
                # Update primvar
                utils.set_primvar(obj, "shaderTag", self.name, override=True)
                
                # Update material if object has slots
                if material and obj.material_slots:
                    obj.material_slots[0].material = material
        
        # Finalize changes
        self.last = self.name
        utils.refresh_shader_tags(context)

class STUDIOTOOLS_ASSET_Properties(bpy.types.PropertyGroup):
    
    name_override: bpy.props.BoolProperty(
        name="Override Existing Names",
        description="",
        default=True
    )

    name_pos: bpy.props.EnumProperty(
        name="Positional Prefix",
        description="",
        items = [
            ("L", "L", "Left"),
            ("C", "C", "Center"),
            ("R", "R", "Right"),
            ("T", "T", "Top"),
            ("B", "B", "Bottom")
        ]
    )

    name_pos_auto: bpy.props.BoolProperty(
        name="Auto Positional Prefix",
        description="",
        default=True
    )

    name_pos_splitaxis: bpy.props.EnumProperty(
        name="Split Axis",
        description="",
        items = [
            ("0", "X-Axis", ""),
            ("1", "Y-Axis", ""),
            ("2", "Z-Axis", ""),
        ],
        default="0"
    )

    name_pos_splittolerance: bpy.props.FloatProperty(
        name="Split Tolerance",
        description="",
        default=0.0
    )

    shader_tag_name: bpy.props.StringProperty(
        name="Tag Name",
        default="tag"
    )

    shader_tags: bpy.props.CollectionProperty(type=STUDIOTOOLS_ASSET_ShaderTag)
    active_shader_tag_index: bpy.props.IntProperty()

classes = [STUDIOTOOLS_ASSET_ShaderTag, STUDIOTOOLS_ASSET_Properties]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.studiotools_asset = bpy.props.PointerProperty(type=STUDIOTOOLS_ASSET_Properties)

def unregister():
    del bpy.types.Scene.studiotools_asset

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)