import os
import re
import shutil
from datetime import datetime

try:
    import bpy
    from bpy.types import Operator
    from bpy.props import StringProperty
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False
    class Operator:
        pass
    class StringProperty:
        def __init__(self, **kwargs): pass
    # Setup dummy bpy module for non-Blender python environments (like syntax checking)
    import sys
    from types import ModuleType
    dummy_bpy = ModuleType("bpy")
    dummy_bpy.props = ModuleType("bpy.props")
    dummy_bpy.props.EnumProperty = lambda **kwargs: None
    dummy_bpy.props.BoolProperty = lambda **kwargs: None
    dummy_bpy.props.StringProperty = lambda **kwargs: None
    sys.modules["bpy"] = dummy_bpy
    bpy = dummy_bpy

from utils import resolve_blend_path, get_published_assets, update_default_asset_name, update_default_render_name, write_simple_yaml, get_render_version_and_paths, setup_render_settings

class WM_OT_studiotools_link_asset(Operator):
    """Link an asset from a copied deliverable path."""
    bl_idname = "wm.studiotools_link_asset"
    bl_label = "Link Asset from Path"
    bl_description = "Resolve and link collections from the copied asset/version folder"
    
    def execute(self, context):
        path_to_import = context.scene.studiotools_import_path.strip()
        if not path_to_import:
            self.report({'WARNING'}, "Please paste a path first.")
            return {'CANCELLED'}
            
        blend_path, ver_dir = resolve_blend_path(path_to_import)
        if not blend_path:
            self.report({'ERROR'}, f"Could not find scene.blend in the provided path: {path_to_import}")
            return {'CANCELLED'}
            
        print(f"[Studio Tools] Resolved link target to: {blend_path}")
        
        try:
            # Load collections list without linking them yet
            with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
                collections = data_from.collections
                
            if not collections:
                # Fallback: link objects instead of collections
                with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
                    data_to.objects = data_from.objects
                
                linked_objects = [obj for obj in data_to.objects if obj]
                if not linked_objects:
                    self.report({'ERROR'}, "No collections or objects found to link in scene.blend.")
                    return {'CANCELLED'}
                    
                # Link objects into active scene collection
                for obj in linked_objects:
                    context.scene.collection.objects.link(obj)
                
                self.report({'INFO'}, f"Linked {len(linked_objects)} objects from asset.")
            else:
                # Link all collections found in the file
                with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
                    data_to.collections = collections
                    
                linked_collections = [col for col in data_to.collections if col]
                for col in linked_collections:
                    context.scene.collection.children.link(col)
                    
                self.report({'INFO'}, f"Linked {len(linked_collections)} collections from asset.")
                
            # Find the library we just linked and mark it as direct
            for lib in bpy.data.libraries:
                lib_path = os.path.abspath(bpy.path.abspath(lib.filepath))
                if lib_path == os.path.abspath(blend_path):
                    lib["studiotools_direct"] = True

            # Clear input field after success
            context.scene.studiotools_import_path = ""
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to link library: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class WM_OT_studiotools_swap_version(Operator):
    """Switch a linked asset library to a different version folder in-place."""
    bl_idname = "wm.studiotools_swap_version"
    bl_label = "Swap Version"
    bl_description = "Swap the version folder filepath of this linked library"
    
    library_name: StringProperty(name="Library Name")
    target_version: StringProperty(name="Target Version")
    
    def execute(self, context):
        lib = bpy.data.libraries.get(self.library_name)
        if not lib:
            self.report({'ERROR'}, f"Linked library '{self.library_name}' not found.")
            return {'CANCELLED'}
            
        norm_path = os.path.abspath(bpy.path.abspath(lib.filepath))
        lib_dir = os.path.dirname(norm_path)
        asset_dir = os.path.dirname(lib_dir)
        
        new_lib_dir = os.path.join(asset_dir, self.target_version)
        new_filepath = os.path.join(new_lib_dir, "scene.blend")
        
        if not os.path.exists(new_filepath):
            self.report({'ERROR'}, f"Target version file does not exist: {new_filepath}")
            return {'CANCELLED'}
            
        # Convert path back to relative if original was relative (starts with //)
        if lib.filepath.startswith("//"):
            lib.filepath = bpy.path.relpath(new_filepath)
        else:
            lib.filepath = new_filepath
            
        try:
            lib.reload()
            # Force redraw of 3D viewports to update visuals instantly
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            self.report({'INFO'}, f"Successfully swapped version to {self.target_version}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to reload library version: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class WM_OT_studiotools_unlink_asset(Operator):
    """Unlink and remove this asset library from the scene."""
    bl_idname = "wm.studiotools_unlink_asset"
    bl_label = "Unlink Asset"
    bl_description = "Unlink this asset library and remove its linked data from the scene"
    
    library_name: StringProperty(name="Library Name")
    
    def execute(self, context):
        lib = bpy.data.libraries.get(self.library_name)
        if not lib:
            self.report({'ERROR'}, f"Library '{self.library_name}' not found.")
            return {'CANCELLED'}
            
        try:
            name = lib.name
            bpy.data.libraries.remove(lib)
            self.report({'INFO'}, f"Unlinked and removed asset library '{name}'.")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to unlink library: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class WM_OT_studiotools_new_file(Operator):
    """Create a new empty workfile for the current task."""
    bl_idname = "wm.studiotools_new_file"
    bl_label = "New Empty Scene"
    bl_description = "Wipe the active file and save it as a new empty workfile version"
    
    def execute(self, context):
        task_path = os.environ.get("ST_CWD")
        if not task_path:
            self.report({'ERROR'}, "ST_CWD environment variable not set.")
            return {'CANCELLED'}
            
        wip_dir = os.path.join(task_path, "wip")
        app_dir = os.path.join(wip_dir, "blender")
        os.makedirs(app_dir, exist_ok=True)
        
        # Determine next version
        version = 1
        if os.path.exists(app_dir):
            for f in os.listdir(app_dir):
                match = re.search(r"scene_v(\d+)\.blend", f, re.IGNORECASE)
                if match:
                    version = max(version, int(match.group(1)) + 1)
                    
        file_name = f"scene_v{version:03d}.blend"
        save_path = os.path.abspath(os.path.join(app_dir, file_name))
        
        try:
            # Wiping the scene collection and data blocks (safest, keeps settings and handlers)
            for col in list(context.scene.collection.children):
                context.scene.collection.children.unlink(col)
                
            for obj in list(bpy.data.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
                
            for col in list(bpy.data.collections):
                if col != context.scene.collection:
                    bpy.data.collections.remove(col)
                    
            for block in [bpy.data.materials, bpy.data.textures, bpy.data.actions, bpy.data.node_groups, bpy.data.libraries]:
                for item in list(block):
                    block.remove(item)
                    
            # Save new file
            bpy.ops.wm.save_as_mainfile(filepath=save_path)
            self.report({'INFO'}, f"Created new empty workfile version: {file_name}")
            
            # Reset default asset name
            if hasattr(bpy.types.Scene, "studiotools_asset_name"):
                context.scene.studiotools_asset_name = "scene"
                
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create new empty workfile: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class WM_OT_studiotools_increment_save(Operator):
    """Save the current workfile as the next version."""
    bl_idname = "wm.studiotools_increment_save"
    bl_label = "Increment Save"
    bl_description = "Save a new copy of the current scene with an incremented version number"
    
    def execute(self, context):
        current_file = bpy.data.filepath
        if not current_file:
            self.report({'ERROR'}, "Current file is not saved. Save it once first.")
            return {'CANCELLED'}
            
        dir_name = os.path.dirname(current_file)
        base_name = os.path.basename(current_file)
        
        # Search for version number pattern like _v001 or v001
        match = re.search(r"(_?v)(\d+)(\.blend)$", base_name, re.IGNORECASE)
        if not match:
            # Fallback if file doesn't follow versioning (e.g. scene.blend)
            new_base_name = base_name.replace(".blend", "_v001.blend")
        else:
            prefix = match.group(1) # e.g. "v" or "_v"
            ver_num = int(match.group(2))
            ext = match.group(3)
            new_ver_num = ver_num + 1
            padding = len(match.group(2))
            new_base_name = re.sub(
                r"(_?v)(\d+)(\.blend)$", 
                f"{prefix}{new_ver_num:0{padding}d}{ext}", 
                base_name, 
                flags=re.IGNORECASE
            )
            
        new_filepath = os.path.abspath(os.path.join(dir_name, new_base_name))
        
        try:
            bpy.ops.wm.save_as_mainfile(filepath=new_filepath)
            self.report({'INFO'}, f"Increment saved to: {new_base_name}")
            
            # Update default asset name to match the new file name
            update_default_asset_name()
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to increment save: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class WM_OT_studiotools_load_usd(Operator):
    """Select and import a published USD asset from project published outputs."""
    bl_idname = "wm.studiotools_load_usd"
    bl_label = "Load USD Asset"
    bl_description = "Select and import a published USD asset"
    
    asset_path: bpy.props.EnumProperty(
        name="Published Asset",
        description="Select a published USD asset in the project",
        items=get_published_assets
    )
    
    def invoke(self, context, event):
        # Open small dialog popup showing our dynamic properties instead of general file browser
        return context.window_manager.invoke_props_dialog(self)
        
    def execute(self, context):
        if self.asset_path == "NONE":
            self.report({'WARNING'}, "No published USD asset selected.")
            return {'CANCELLED'}
            
        try:
            # Import the selected USD file using Blender's native USD importer
            bpy.ops.wm.usd_import(filepath=self.asset_path)
            self.report({'INFO'}, f"Successfully loaded USD: {os.path.basename(self.asset_path)}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import USD: {str(e)}")
            return {'CANCELLED'}

class WM_OT_studiotools_publish_usd(Operator):
    """Export the current scene as a published USD asset and save metadata."""
    bl_idname = "wm.studiotools_publish_usd"
    bl_label = "Publish USD Asset"
    bl_description = "Export the current scene as a published USD asset"
    
    def execute(self, context):
        task_path = os.environ.get("ST_CWD")
        if not task_path:
            self.report({'ERROR'}, "ST_CWD environment variable not set.")
            return {'CANCELLED'}
            
        try:
            # 1. Save active Blend file
            bpy.ops.wm.save_mainfile()
            current_blend = bpy.data.filepath
            
            # 2. Determine versions directory packaged in a folder
            versions_dir = os.path.join(task_path, "versions")
            os.makedirs(versions_dir, exist_ok=True)
            
            # 3. Determine next version by scanning versions directory folders
            version = 1
            asset_prefix = context.scene.studiotools_asset_name.strip()
            if not asset_prefix:
                asset_prefix = "scene"
            # Strip any version suffix (e.g. _v001, -v1, v3) entered by the user
            asset_prefix = re.sub(r"[._-]?v\d+$", "", asset_prefix, flags=re.IGNORECASE)
            asset_prefix = re.sub(r"[^a-zA-Z0-9_]", "_", asset_prefix)
            
            asset_versions_dir = os.path.join(versions_dir, asset_prefix)
            if os.path.exists(asset_versions_dir):
                for f in os.listdir(asset_versions_dir):
                    if os.path.isdir(os.path.join(asset_versions_dir, f)):
                        match = re.search(r"^v(\d+)", f, re.IGNORECASE)
                        if match:
                            version = max(version, int(match.group(1)) + 1)
                        
            version_folder = os.path.join(asset_prefix, f"v{version:03d}")
            version_dir = os.path.join(versions_dir, version_folder)
            os.makedirs(version_dir, exist_ok=True)
            
            export_as_usdc = context.scene.studiotools_export_usdc
            # Blender uses file extension to determine format (ascii .usda vs binary .usdc/.usd).
            # To ensure the file is always named stage.usd on disk, we export with Blender's preferred
            # extension first, then rename it to stage.usd if it was exported as .usda.
            temp_ext = ".usd" if export_as_usdc else ".usda"
            pub_filepath = os.path.join(version_dir, f"stage{temp_ext}")

            
            # 4. Export scene as USD (USDA ascii layout for human readable composition verification)
            export_props = bpy.ops.wm.usd_export.get_rna_type().properties
            kwargs = {}
            export_animation = context.scene.studiotools_export_animation
            if "export_animation" in export_props:
                kwargs["export_animation"] = export_animation
            if "export_hair" in export_props:
                kwargs["export_hair"] = True
            if "export_uvmaps" in export_props:
                kwargs["export_uvmaps"] = True
            if "rename_uvmaps" in export_props:
                kwargs["rename_uvmaps"] = True
            if "export_mesh_colors" in export_props:
                kwargs["export_mesh_colors"] = True
            if "export_normals" in export_props:
                kwargs["export_normals"] = True
            if "export_materials" in export_props:
                kwargs["export_materials"] = True
            if "export_subdivision" in export_props:
                kwargs["export_subdivision"] = "BEST_MATCH"
            if "export_armatures" in export_props:
                kwargs["export_armatures"] = True
            if "only_deform_bones" in export_props:
                kwargs["only_deform_bones"] = False
            if "export_shapekeys" in export_props:
                kwargs["export_shapekeys"] = True
            if "use_instancing" in export_props:
                kwargs["use_instancing"] = True
            if "evaluation_mode" in export_props:
                kwargs["evaluation_mode"] = "RENDER"
            if "generate_preview_surface" in export_props:
                kwargs["generate_preview_surface"] = True
            if "generate_materialx_network" in export_props:
                kwargs["generate_materialx_network"] = False
            if "convert_orientation" in export_props:
                kwargs["convert_orientation"] = True
            if "export_custom_properties" in export_props:
                kwargs["export_custom_properties"] = True
            if "custom_properties_namespace" in export_props:
                kwargs["custom_properties_namespace"] = ""
            if "author_blender_name" in export_props:
                kwargs["author_blender_name"] = False
            if "convert_world_material" in export_props:
                kwargs["convert_world_material"] = False
            if "export_meshes" in export_props:
                kwargs["export_meshes"] = True
            if "export_lights" in export_props:
                kwargs["export_lights"] = True
            if "export_cameras" in export_props:
                kwargs["export_cameras"] = True
            if "export_curves" in export_props:
                kwargs["export_curves"] = True
            if "export_points" in export_props:
                kwargs["export_points"] = True
            if "export_volumes" in export_props:
                kwargs["export_volumes"] = True
            if "merge_parent_xform" in export_props:
                kwargs["merge_parent_xform"] = True
            if "convert_scene_unit" in export_props:
                kwargs["convert_scene_unit"] = "METERS"
            if "meters_per_unit" in export_props:
                kwargs["meters_per_unit"] = 1.0
                
            bpy.ops.wm.usd_export(filepath=pub_filepath, **kwargs)

            # If exported as stage.usda, rename it to stage.usd so it is always stage.usd on disk
            final_pub_filepath = os.path.join(version_dir, "stage.usd")
            if not export_as_usdc:
                if os.path.exists(pub_filepath):
                    if os.path.exists(final_pub_filepath):
                        os.remove(final_pub_filepath)
                    os.rename(pub_filepath, final_pub_filepath)
            
            pub_filepath = final_pub_filepath
            pub_filename = "stage.usd"

            # 4b. Capture the current 3D viewport as thumbnail.png
            thumb_path = os.path.join(version_dir, "thumbnail.png")
            try:
                scene = bpy.context.scene
                # Stash original render output settings
                orig_filepath       = scene.render.filepath
                orig_format         = scene.render.image_settings.file_format
                orig_res_x          = scene.render.resolution_x
                orig_res_y          = scene.render.resolution_y
                orig_res_pct        = scene.render.resolution_percentage
                orig_use_overwrite  = scene.render.use_overwrite

                # Configure for a compact 960×540 PNG thumbnail
                scene.render.filepath                    = thumb_path
                scene.render.image_settings.file_format = "PNG"
                scene.render.resolution_x               = 960
                scene.render.resolution_y               = 540
                scene.render.resolution_percentage      = 100
                scene.render.use_overwrite               = True

                # Render the OpenGL viewport (uses current shading / camera / view)
                bpy.ops.render.opengl(write_still=True)

                # Restore all original settings
                scene.render.filepath                    = orig_filepath
                scene.render.image_settings.file_format = orig_format
                scene.render.resolution_x               = orig_res_x
                scene.render.resolution_y               = orig_res_y
                scene.render.resolution_percentage      = orig_res_pct
                scene.render.use_overwrite               = orig_use_overwrite

                print(f"[Studio Tools] Saved viewport thumbnail: {thumb_path}")
            except Exception as thumb_err:
                print(f"[Studio Tools] Warning: Could not capture viewport thumbnail: {thumb_err}")

            # Save a copy of the active .blend file inside the version directory
            if current_blend and os.path.exists(current_blend):
                blend_copy_name = "scene.blend"
                blend_copy_path = os.path.join(version_dir, blend_copy_name)
                try:
                    # Temporarily convert relative paths to absolute so the copied file's links don't break
                    bpy.ops.file.make_paths_absolute()
                    bpy.ops.wm.save_mainfile()
                    
                    # Copy the file with absolute paths
                    shutil.copy2(current_blend, blend_copy_path)
                    print(f"[Studio Tools] Exported .blend copy with absolute library paths to: {blend_copy_path}")
                    
                    # Revert active file back to relative paths for portability
                    bpy.ops.file.make_paths_relative()
                    bpy.ops.wm.save_mainfile()
                except Exception as bce:
                    print(f"[Studio Tools] Warning: Failed to export .blend copy: {bce}")
                    # Attempt cleanup of paths if something failed
                    try:
                        bpy.ops.file.make_paths_relative()
                        bpy.ops.wm.save_mainfile()
                    except Exception:
                        pass
            
            # 5. Write metadata
            meta_path = os.path.join(version_dir, "metadata.yaml")
            exported_objs = [obj.name for obj in bpy.context.scene.objects if not obj.parent]
            
            meta_data = {
                "type": "usd_publish",
                "application": "blender",
                "application_version": os.environ.get("ST_APP_VERSION") or bpy.app.version_string,
                "source_scene": current_blend if current_blend else "",
                "source_file": os.path.basename(current_blend) if current_blend else "unsaved.blend",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": os.environ.get("USER", "artist"),
                "exported_root_objects": exported_objs
            }
            write_simple_yaml(meta_path, meta_data)
            
            # Create symlink if "Mark as Published" is checked
            mark_as_published = context.scene.studiotools_mark_as_published
            if mark_as_published:
                published_dir = os.path.join(task_path, "published")
                os.makedirs(published_dir, exist_ok=True)
                symlink_path = os.path.join(published_dir, asset_prefix)
                
                if os.path.islink(symlink_path) or os.path.exists(symlink_path):
                    if os.path.isdir(symlink_path) and not os.path.islink(symlink_path):
                        shutil.rmtree(symlink_path)
                    else:
                        os.remove(symlink_path)
                        
                src = os.path.join("..", "versions", version_folder)
                try:
                    os.symlink(src, symlink_path)
                    print(f"[Studio Tools] Created published symlink: {symlink_path} -> {src}")
                except Exception as se:
                    print(f"[Studio Tools] Warning: Failed to create symlink: {se}")
            
            # 6. Version up the WIP scene file (Save-up on publish)
            wip_version_msg = ""
            try:
                current_blend = bpy.data.filepath
                wip_dir = os.path.dirname(current_blend) if current_blend else os.path.join(task_path, "wip", "blender")
                
                # Determine next wip version
                wip_version = 1
                if os.path.exists(wip_dir):
                    for f in os.listdir(wip_dir):
                        match = re.search(r"scene_v(\d+)\.blend", f, re.IGNORECASE)
                        if match:
                            wip_version = max(wip_version, int(match.group(1)) + 1)
                
                new_wip_filename = f"scene_v{wip_version:03d}.blend"
                new_wip_path = os.path.abspath(os.path.join(wip_dir, new_wip_filename))
                
                bpy.ops.wm.save_as_mainfile(filepath=new_wip_path)
                wip_version_msg = f"WIP Versioned Up: {new_wip_filename}"
                print(f"[Studio Tools] Versioned up WIP scene file to: {new_wip_path}")
            except Exception as ve:
                print(f"[Studio Tools] Warning: Failed to version up WIP scene file: {ve}")
                
            self.report({'INFO'}, f"Successfully published USD asset: {pub_filename}")
            
            # Show success dialog popup inside Blender
            def draw_popup(self, context):
                self.layout.label(text=f"Published USD Asset: {pub_filename}", icon='CHECKMARK')
                self.layout.label(text=f"Version: v{version:03d}")
                if wip_version_msg:
                    self.layout.label(text=wip_version_msg, icon='FILE_BLEND')
                self.layout.label(text=f"Metadata saved to: {os.path.basename(meta_path)}")
            
            context.window_manager.popup_menu(draw_popup, title="Publish Successful", icon='INFO')
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to publish USD: {str(e)}")
            return {'CANCELLED'}

def capture_thumbnail(scene, version_dir):
    """Captures a viewport thumbnail using OpenGL render and saves it as thumbnail.png."""
    thumb_path = os.path.join(version_dir, "thumbnail.png")
    try:
        # Stash original render output settings
        orig_filepath       = scene.render.filepath
        orig_format         = scene.render.image_settings.file_format
        orig_res_x          = scene.render.resolution_x
        orig_res_y          = scene.render.resolution_y
        orig_res_pct        = scene.render.resolution_percentage
        orig_use_overwrite  = scene.render.use_overwrite

        # Configure for a compact 960×540 PNG thumbnail
        scene.render.filepath                    = thumb_path
        scene.render.image_settings.file_format = "PNG"
        scene.render.resolution_x               = 960
        scene.render.resolution_y               = 540
        scene.render.resolution_percentage      = 100
        scene.render.use_overwrite               = True

        # Render the OpenGL viewport (uses current shading / camera / view)
        bpy.ops.render.opengl(write_still=True)

        # Restore all original settings
        scene.render.filepath                    = orig_filepath
        scene.render.image_settings.file_format = orig_format
        scene.render.resolution_x               = orig_res_x
        scene.render.resolution_y               = orig_res_y
        scene.render.resolution_percentage      = orig_res_pct
        scene.render.use_overwrite               = orig_use_overwrite
        print(f"[Studio Tools] Viewport thumbnail saved to {thumb_path}")
    except Exception as thumb_err:
        print(f"[Studio Tools] Warning: Failed to capture render thumbnail: {thumb_err}")

def write_metadata(context, version_dir, render_path, version_int, start_frame, end_frame, render_type):
    """Writes a pipeline-compliant metadata.yaml describing the render."""
    try:
        scene = context.scene
        current_blend = bpy.data.filepath
        render_name = scene.studiotools_render_name.strip()
        render_name = re.sub(r"[^a-zA-Z0-9_]", "_", render_name)
        
        meta_path = os.path.join(version_dir, "metadata.yaml")
        
        if render_type == 'playblast':
            file_format = "jpg"
            codec = "quality_90"
            color_depth = "8"
            type_val = "blender_playblast"
        else:
            file_format = "exr"
            codec = "DWAA"
            color_depth = "16"
            type_val = "blender_render"
            
        meta_data = {
            "type": type_val,
            "application": "blender",
            "application_version": os.environ.get("ST_APP_VERSION") or bpy.app.version_string,
            "source_scene": current_blend if current_blend else "",
            "source_file": os.path.basename(current_blend) if current_blend else "unsaved.blend",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": os.environ.get("USER", "artist"),
            "render_name": render_name,
            "version": version_int,
            "frame_range": f"{start_frame}-{end_frame}",
            "file_format": file_format,
            "codec": codec,
            "color_depth": color_depth
        }
        write_simple_yaml(meta_path, meta_data)
        print(f"[Studio Tools] Wrote render metadata to {meta_path}")
    except Exception as meta_err:
        print(f"[Studio Tools] Warning: Failed to write metadata.yaml for render: {meta_err}")

class WM_OT_studiotools_render_still(Operator):
    """Render the current frame as a multilayer EXR sequence (single frame version)."""
    bl_idname = "wm.studiotools_render_still"
    bl_label = "Render Still Frame"
    bl_description = "Configure rendering, save a viewport thumbnail, render the current frame as EXR, and write metadata"

    def execute(self, context):
        task_path = os.environ.get("ST_CWD")
        if not task_path:
            self.report({'ERROR'}, "ST_CWD environment variable not set.")
            return {'CANCELLED'}

        scene = context.scene
        render_name = scene.studiotools_render_name.strip()
        if not render_name:
            self.report({'ERROR'}, "Please specify a Render Name.")
            return {'CANCELLED'}

        # Calculate version and target path dynamically
        version, version_dir, filename, filepath = get_render_version_and_paths(
            task_path, render_name, 'exr', create_dirs=True
        )

        # Configure render settings
        setup_render_settings(scene, 'exr', filepath)

        # Capture viewport thumbnail first
        capture_thumbnail(scene, version_dir)

        # Render the current frame using animation=True so frame padding is preserved
        current_frame = scene.frame_current
        orig_start = scene.frame_start
        orig_end = scene.frame_end

        scene.frame_start = current_frame
        scene.frame_end = current_frame

        print(f"[Studio Tools] Initiating render still frame {current_frame}: {filepath}")
        try:
            bpy.ops.render.render(animation=True)
        except Exception as render_err:
            self.report({'ERROR'}, f"Render failed: {str(render_err)}")
            # Restore original frames
            scene.frame_start = orig_start
            scene.frame_end = orig_end
            return {'CANCELLED'}

        # Restore original frames
        scene.frame_start = orig_start
        scene.frame_end = orig_end

        # Write metadata
        write_metadata(context, version_dir, filepath, version, current_frame, current_frame, 'exr')

        self.report({'INFO'}, f"Render still frame completed successfully!")

        # Show success dialog
        def draw_popup(self, context):
            self.layout.label(text="Render Still Complete!", icon='CHECKMARK')
            self.layout.label(text=f"Folder: v{version:03d}")
            self.layout.label(text=f"Frame: {current_frame}")
            self.layout.label(text=f"Output: {filename}")
            
        context.window_manager.popup_menu(draw_popup, title="Render Success", icon='INFO')
        return {'FINISHED'}

class WM_OT_studiotools_render_sequence(Operator):
    """Execute sequence render and write pipeline metadata."""
    bl_idname = "wm.studiotools_render_sequence"
    bl_label = "Render Animation"
    bl_description = "Execute render sequence, capture viewport thumbnail, and write StudioTools metadata"
    
    def execute(self, context):
        task_path = os.environ.get("ST_CWD")
        if not task_path:
            self.report({'ERROR'}, "ST_CWD environment variable not set.")
            return {'CANCELLED'}
            
        scene = context.scene
        render_name = scene.studiotools_render_name.strip()
        if not render_name:
            self.report({'ERROR'}, "Please specify a Render Name.")
            return {'CANCELLED'}

        # Calculate version and target path dynamically
        version, version_dir, filename, filepath = get_render_version_and_paths(
            task_path, render_name, 'exr', create_dirs=True
        )

        # Configure render settings
        setup_render_settings(scene, 'exr', filepath)
        
        # Capture viewport thumbnail first
        capture_thumbnail(scene, version_dir)
            
        # Trigger Blender render animation (blocks until finished)
        print(f"[Studio Tools] Initiating render sequence: {filepath}")
        try:
            bpy.ops.render.render(animation=True)
        except Exception as render_err:
            self.report({'ERROR'}, f"Render failed: {str(render_err)}")
            return {'CANCELLED'}
            
        # Write pipeline metadata
        write_metadata(context, version_dir, filepath, version, scene.frame_start, scene.frame_end, 'exr')
            
        self.report({'INFO'}, f"Render sequence completed successfully!")
        
        # Show success dialog
        def draw_popup(self, context):
            self.layout.label(text="Render Sequence Complete!", icon='CHECKMARK')
            self.layout.label(text=f"Folder: v{version:03d}")
            self.layout.label(text=f"Frames: {scene.frame_start} - {scene.frame_end}")
            self.layout.label(text=f"Output: {filename}")
            
        context.window_manager.popup_menu(draw_popup, title="Render Success", icon='INFO')
        return {'FINISHED'}

class WM_OT_studiotools_render_playblast(Operator):
    """Execute viewport animation capture as a JPEG sequence."""
    bl_idname = "wm.studiotools_render_playblast"
    bl_label = "Render Playblast"
    bl_description = "Capture viewport animation as a JPEG sequence, save thumbnail, and write metadata"

    def execute(self, context):
        task_path = os.environ.get("ST_CWD")
        if not task_path:
            self.report({'ERROR'}, "ST_CWD environment variable not set.")
            return {'CANCELLED'}

        scene = context.scene
        render_name = scene.studiotools_render_name.strip()
        if not render_name:
            self.report({'ERROR'}, "Please specify a Render Name.")
            return {'CANCELLED'}

        # Calculate version and target path dynamically for playblast
        version, version_dir, filename, filepath = get_render_version_and_paths(
            task_path, render_name, 'playblast', create_dirs=True
        )

        # Configure render settings
        setup_render_settings(scene, 'playblast', filepath)

        # Capture viewport thumbnail first
        capture_thumbnail(scene, version_dir)

        # Trigger Blender OpenGL animation capture (blocks until finished)
        print(f"[Studio Tools] Initiating playblast animation capture: {filepath}")
        try:
            bpy.ops.render.opengl(animation=True)
        except Exception as render_err:
            self.report({'ERROR'}, f"Playblast failed: {str(render_err)}")
            return {'CANCELLED'}

        # Write pipeline metadata
        write_metadata(context, version_dir, filepath, version, scene.frame_start, scene.frame_end, 'playblast')

        self.report({'INFO'}, f"Playblast sequence completed successfully!")

        # Show success dialog
        def draw_popup(self, context):
            self.layout.label(text="Playblast Complete!", icon='CHECKMARK')
            self.layout.label(text=f"Folder: v{version:03d}")
            self.layout.label(text=f"Frames: {scene.frame_start} - {scene.frame_end}")
            self.layout.label(text=f"Output: {filename}")
            
        context.window_manager.popup_menu(draw_popup, title="Playblast Success", icon='INFO')
        return {'FINISHED'}

