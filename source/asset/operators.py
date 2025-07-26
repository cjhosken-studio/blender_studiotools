import bpy
import bmesh
import random
from .. import utils

class STUDIOTOOLS_ASSET_OT_AddShaderTag(bpy.types.Operator):
    bl_idname = "studiotools_asset.add_shadertag"
    bl_label = "Add Shader Tag"
    
    def execute(self, context):
        scene = context.scene
        
        return {'FINISHED'}
    
class STUDIOTOOLS_ASSET_OT_RemoveShaderTag(bpy.types.Operator):
    bl_idname = "studiotools_asset.remove_shadertag"
    bl_label = "Remove Shader Tag"
    
    def execute(self, context):
        scene = context.scene
        
        return {'FINISHED'}

class STUDIOTOOLS_ASSET_OT_ReloadShaderTags(bpy.types.Operator):
    bl_idname = "studiotools_asset.reload_shadertags"
    bl_label = "Reload Shader Tags"
    
    def execute(self, context):
        scene = context.scene
        
        return {'FINISHED'}

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
        studiotools_asset = scene.studiotools_asset

        objects = []

        if (studiotools.selection_type == "OBJ"):
            objects = context.selected_objects
        else:
            objects = utils.get_all_objects_from_collection(studiotools.selected_collection)

        name_counter = {}

        for obj in objects:

            pos = studiotools_asset.name_pos

            if (studiotools_asset.name_pos_auto):
                p = obj.location[int(studiotools_asset.name_pos_splitaxis)]
                if abs(p) > studiotools_asset.name_pos_splittolerance:
                    pos = "L" if p > 0 else "R"
                else:
                    pos = "C"

            name = obj.name

            result, data = utils.validate_name(obj.name)
            if (result):
                name = data[1]

            name_counter[name] = name_counter.get(name, 0) + 1
            variant = f"{name_counter[name]:04d}"  # Format as 4-digit number

            if obj.type == "MESH":
                ext = "GEP"

                for mod in obj.modifiers:
                    if mod.type == "SUBSURF":
                        ext = "GES"
                        break
                
                if obj.hide_render:
                    ext = "PLY"

            elif obj.type in ["CURVE", "CURVES"]:
                ext = "CRV"
            elif obj.type == "FONT":
                ext = "TXT"
            elif obj.type == "POINTCLOUD":
                ext = "PNT"
            elif obj.type == "VOLUME":
                ext = "VOL"
            elif obj.type == "GREASESPENCIL":
                ext = "GSP"
            elif obj.type in ["SURFACE", "META"]:
                ext == "NUB"
            elif obj.type == "ARMATURE":
                ext == "RIG"
            elif obj.type == "LATTICE":
                ext == "LAT"
            elif obj.type in ["LIGHT", "LIGHT_PROBE"]:
                ext = "LGT"
            elif obj.type == "CAMERA":
                ext = "CAM"
            elif obj.type == "SPEAKER":
                ext = "AUD"
            elif obj.type == "EMPTY":
                ext = "LOC"
            else:
                ext = "UNK"

            if result and studiotools_asset.name_override:
                obj.name = f"{pos}_{name}_{variant}_{ext}"
                obj.data.name = obj.name
            else:
                if not result:
                    obj.name = f"{pos}_{name}_{variant}_{ext}"
                    obj.data.name = obj.name
                
        return {'FINISHED'}

class STUDIOTOOLS_ASSET_OT_Validate(bpy.types.Operator):
    bl_idname = "studiotools_asset.validate"
    bl_label = "Validate"
    
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
            objects = utils.get_all_objects_from_collection(studiotools.selected_collection)

        num_errors = 0
        num_warnings = 0

        print("\nValidating Objects...\n")

        for obj in objects:
            validation_error_prefix = f"ERROR ({obj.name}):"
            validation_warning_prefix = f"WARNING ({obj.name})"

            result, data = utils.validate_name(obj.name)
            if not result:
                num_errors += 1
                print(validation_error_prefix, data)

            if any(abs(s-1.0) > 0.001 for s in obj.scale):
                num_warnings += 1
                print(validation_warning_prefix, "Scale is not uniformly 1. Apply scale to fix.")

            if obj.type == 'MESH':
                # Check for invalid geometry
                mesh = obj.data
                if not mesh.polygons and not mesh.edges:
                    num_errors += 1
                    print(validation_error_prefix, "Mesh has no valid geometry.")

                # Check for ngons
                if any(len(p.vertices) > 4 for p in mesh.polygons):
                    num_errors += 1
                    print(validation_error_prefix, "Mesh contains ngons (faces with >4 vertices).")

                # Check for non-manifold geometry
                bm = bmesh.new()
                bm.from_mesh(mesh)
                if any(e for e in bm.edges if not e.is_manifold):
                    num_errors += 1
                    print(validation_error_prefix, "Mesh has non-manifold edges.")
                bm.free()

                subdiv_mods = [mod for mod in obj.modifiers if mod.type == 'SUBSURF']
                if subdiv_mods:
                    last_mod = obj.modifiers[-1]
                    if not subdiv_mods[-1] == last_mod:
                        num_warnings += 1
                        print(validation_warning_prefix, 
                             f"Subdivision modifier '{subdiv_mods[-1].name}' is overshadowed by other modifiers. This may be applied in USD exports.")

        print("")
        if num_errors:
            print("Validation: FAILED")
            print(f"Objects Checked: {len(objects)}")
            print(f"Errors: {num_errors}")
            print(f"Warnings: {num_warnings}")
            utils.show_popup("Validation Failed!", f"Validation failed with {num_errors} errors and {num_warnings} warnings. See the console for a full error list.", "ERROR")
        else:
            utils.show_popup("Validation Passed!", f"Validation passed with {num_warnings} warnings. You are free to export!")
            print("Validation: PASSED")
            print(f"Objects Checked: {len(objects)}")
            print(f"Warnings: {num_warnings}")
        
        return {'FINISHED'}




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
            unique_name = utils.find_unique_name(studiotools_asset.shader_tag_name, existing_names)
            
            # Add new tag with unique name
            tag = studiotools_asset.shader_tags.add()
            tag.name = unique_name
            tag.last = unique_name

        utils.refresh_shader_tags(context)

        return {'FINISHED'}

# Operator to remove a shader tag
class STUDIOTOOLS_ASSET_OT_RemoveShaderTag(bpy.types.Operator):
    bl_idname = "studiotools_asset.shadertag_remove"
    bl_label = "Remove Shader Tag"
    bl_description = "Remove this shader tag from the object"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        studiotools_asset = context.scene.studiotools_asset
        tag_name = studiotools_asset.shader_tags[self.index].name
            
        for obj in bpy.data.objects:
            print("OBJECT TAG:", tag_name)
            if utils.validate_primvar(obj, "shaderTag", tag_name):
                print("SHADER_TAG", obj["shaderTag"])
                utils.remove_primvar(obj, "shaderTag")

        studiotools_asset.shader_tags.remove(self.index)

        utils.refresh_shader_tags(context)
        
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
            objects = utils.get_all_objects_from_collection(studiotools.selected_collection)

        for obj in objects:
            utils.set_primvar(obj, "shaderTag", studiotools_asset.shader_tags[studiotools_asset.active_shader_tag_index].name, True)

        utils.refresh_shader_tags(context) 

        return {"FINISHED"}
    
# Operator to refresh materials based on tags
class STUDIOTOOLS_ASSET_OT_RefreshShaderTags(bpy.types.Operator):
    bl_idname = "studiotools_asset.shadertag_refresh"
    bl_label = "Refresh Shader Tags"
    bl_description = "Apply all enabled tags to their objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):    
        utils.refresh_shader_tags(context)        
        return {'FINISHED'}

classes = [STUDIOTOOLS_ASSET_OT_Validate, STUDIOTOOLS_ASSET_OT_Rename, STUDIOTOOLS_ASSET_OT_AddShaderTag, STUDIOTOOLS_ASSET_OT_RemoveShaderTag, STUDIOTOOLS_ASSET_OT_RefreshShaderTags, STUDIOTOOLS_ASSET_OT_AssignShaderTag]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)