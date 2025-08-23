import bpy # type: ignore
import re
import os
from . import utils as asset_utils
from .. import utils as global_utils
from .. import io

class STUDIOTOOLS_ASSET_OT_Rename(bpy.types.Operator):
    bl_idname = "studiotools_asset.rename"
    bl_label = "Rename"

    @classmethod
    def poll(cls, context):
        studiotools = context.scene.studiotools
        if (studiotools.selection_type == "OBJ"):
            return len(context.selected_objects) > 0
        else:
            return studiotools.selected_collection
            
    def execute(self, context):
        scene = context.scene
        studiotools = scene.studiotools

        objects = []

        if (studiotools.selection_type == "OBJ"):
            objects = context.selected_objects
        else:
            objects = global_utils.get_all_objects_from_collection(studiotools.selected_collection)

        asset_utils.rename(objects)
                
        return {'FINISHED'}

class STUDIOTOOLS_ASSET_OT_Validate(bpy.types.Operator):
    bl_idname = "studiotools_asset.validate"
    bl_label = "Validate"
    
    @classmethod
    def poll(cls, context):
        studiotools = context.scene.studiotools
        return studiotools.selected_collection

    def execute(self, context):
        scene = context.scene
        studiotools = scene.studiotools

        objects = global_utils.get_all_objects_from_collection(studiotools.selected_collection)

        valid, errors, warnings = asset_utils.validate(objects)

        if valid:   
            global_utils.show_popup("Validation Passed!", f"Validation passed with {warnings} warnings. You are free to export!")
        else:
            global_utils.show_popup("Validation Failed!", f"Validation failed with {errors} errors and {warnings} warnings. See the console for a full error list.", "ERROR")

        return { "FINISHED" }


class STUDIOTOOLS_ASSET_OT_AddShaderTag(bpy.types.Operator):
    bl_idname = "studiotools_asset.shadertag_add"
    bl_label = "Add Shader Tag"
    bl_description = "Add a new shader tag to the selected object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        studiotools_asset = context.scene.studiotools_asset

        if studiotools_asset.shader_tag_name:
            # Get all existing tag names
            existing_names = [tag.name for tag in studiotools_asset.shader_tags]
            
            # Generate unique name
            unique_name = asset_utils.find_unique_name(studiotools_asset.shader_tag_name, existing_names)
            
            # Add new tag with unique name
            tag = studiotools_asset.shader_tags.add()
            tag.name = unique_name
            tag.last = unique_name

        asset_utils.refresh_shader_tags(context)

        return {'FINISHED'}

# Operator to remove a shader tag
class STUDIOTOOLS_ASSET_OT_RemoveShaderTag(bpy.types.Operator):
    bl_idname = "studiotools_asset.shadertag_remove"
    bl_label = "Remove Shader Tag"
    bl_description = "Remove this shader tag from the object"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty() # type: ignore

    def execute(self, context):
        studiotools_asset = context.scene.studiotools_asset
        tag_name = studiotools_asset.shader_tags[self.index].name
            
        for obj in bpy.data.objects:
            print("OBJECT TAG:", tag_name)
            if global_utils.validate_primvar(obj, "shaderTag", tag_name):
                print("SHADER_TAG", obj["shaderTag"])
                global_utils.remove_primvar(obj, "shaderTag")

        studiotools_asset.shader_tags.remove(self.index)

        asset_utils.refresh_shader_tags(context)
        
        return {'FINISHED'}

    
# Operator to refresh materials based on tags
class STUDIOTOOLS_ASSET_OT_AssignShaderTag(bpy.types.Operator):
    bl_idname = "studiotools_asset.shadertag_assign"
    bl_label = "Assign Shader Tags"
    bl_description = "Apply all enabled tags to their objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        studiotools = context.scene.studiotools
        if (studiotools.selection_type == "OBJ"):
            return len(context.selected_objects) > 0
        else:
            return studiotools.selected_collection
        

    def execute(self, context):
        scene = context.scene
        studiotools = scene.studiotools
        studiotools_asset = scene.studiotools_asset

        objects = []

        if (studiotools.selection_type == "OBJ"):
            objects = context.selected_objects
        else:
            objects = global_utils.get_all_objects_from_collection(studiotools.selected_collection)

        for obj in objects:
            global_utils.set_primvar(obj, "shaderTag", studiotools_asset.shader_tags[studiotools_asset.active_shader_tag_index].name, True)

        asset_utils.refresh_shader_tags(context) 

        return {"FINISHED"}
    
# Operator to refresh materials based on tags
class STUDIOTOOLS_ASSET_OT_RefreshShaderTags(bpy.types.Operator):
    bl_idname = "studiotools_asset.shadertag_refresh"
    bl_label = "Refresh Shader Tags"
    bl_description = "Apply all enabled tags to their objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):    
        asset_utils.refresh_shader_tags(context)        
        return {'FINISHED'}
    

class STUDIOTOOLS_ASSET_OT_Export(bpy.types.Operator):
    bl_idname = "studiotools_asset.export"
    bl_label = "Export Asset"
    bl_description = "Export Asset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        studiotools = context.scene.studiotools
        return studiotools.selected_collection

    def execute(self, context):
        studiotools = context.scene.studiotools

        version = "_v001"
        blend_filepath = bpy.data.filepath

        if blend_filepath:
            base_path, ext = os.path.splitext(blend_filepath)

            version_match = re.search(r'(_v|_)(\d+)$', base_path)
            if version_match:
                version = version_match.group(0)
        else:
            global_utils.save_version()

        current_file = bpy.data.filepath
        task = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        versions_folder = os.path.join(task, "versions")

        asset_folder = f"{os.path.basename(task)}{version}"
    
        filepath = os.path.abspath(os.path.join(versions_folder, asset_folder))

        success = io.export(filepath=filepath, root_collection=studiotools.selected_collection, export_asset=True)   
        if success:
            global_utils.show_popup("Export Complete!", f"Asset exported to {filepath}", "INFO")
            global_utils.save_version()

        return {'FINISHED'}
    
    def invoke(self, context, event):
        studiotools = context.scene.studiotools
        valid, errors, warnings = asset_utils.validate(studiotools.selected_collection.all_objects)

        if valid:
            return self.execute(context)
        else:
            return context.window_manager.invoke_confirm(self, event, title="Validation Error", message=f"Validation failed with {errors} errors and {warnings} warnings (see console). Are you sure you want to export?")

classes = [STUDIOTOOLS_ASSET_OT_Validate, STUDIOTOOLS_ASSET_OT_Rename, STUDIOTOOLS_ASSET_OT_AddShaderTag, STUDIOTOOLS_ASSET_OT_RemoveShaderTag, STUDIOTOOLS_ASSET_OT_RefreshShaderTags, STUDIOTOOLS_ASSET_OT_AssignShaderTag, STUDIOTOOLS_ASSET_OT_Export]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)