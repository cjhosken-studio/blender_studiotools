import os
import sys
import re
from datetime import datetime

try:
    import bpy
    from bpy_extras.io_utils import ImportHelper
    from bpy.props import StringProperty
    from bpy.types import Operator, Panel
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

def write_simple_yaml(path, data):
    """Writes a dictionary as a simple YAML file to avoid PyYAML dependencies inside Blender's python."""
    try:
        import yaml
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
    except ImportError:
        # Fallback manual YAML serialization
        with open(path, "w", encoding="utf-8") as f:
            for k, v in data.items():
                if isinstance(v, list):
                    f.write(f"{k}:\n")
                    for item in v:
                        f.write(f"  - \"{item}\"\n")
                else:
                    # Escape quotes in string if necessary
                    escaped_v = str(v).replace('"', '\\"')
                    f.write(f"{k}: \"{escaped_v}\"\n")

# --- Operators ---

def get_published_assets(self, context):
    """Callback to dynamically compile a list of all published USD assets in the project."""
    task_path = os.environ.get("ST_CWD")
    if not task_path:
        return [("NONE", "Pipeline environment context not set!", "")]
        
    sandbox_dir = os.path.dirname(os.path.dirname(task_path))
    assets = []
    
    if os.path.exists(sandbox_dir):
        for root, dirs, files in os.walk(sandbox_dir):
            if os.path.basename(root) == "published":
                for f in files:
                    if f.lower().endswith((".usd", ".usda", ".usdc")):
                        full_path = os.path.abspath(os.path.join(root, f))
                        rel_path = os.path.relpath(full_path, sandbox_dir)
                        assets.append((full_path, rel_path, f"Version: {f}"))
                        
    if not assets:
        return [("NONE", "No published assets found in active project!", "")]
        
    # Sort assets by relative path for consistent logical view
    assets.sort(key=lambda x: x[1])
    return assets

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
            
            if os.path.exists(versions_dir):
                for f in os.listdir(versions_dir):
                    if os.path.isdir(os.path.join(versions_dir, f)):
                        match = re.search(rf"^{re.escape(asset_prefix)}_v(\d+)", f, re.IGNORECASE)
                        if match:
                            version = max(version, int(match.group(1)) + 1)
                        
            version_folder = f"{asset_prefix}_v{version:03d}"
            version_dir = os.path.join(versions_dir, version_folder)
            os.makedirs(version_dir, exist_ok=True)
            
            export_as_usdc = context.scene.studiotools_export_usdc
            usd_ext = ".usdc" if export_as_usdc else ".usda"
            pub_filename = f"{asset_prefix}_v{version:03d}{usd_ext}"
            pub_filepath = os.path.join(version_dir, pub_filename)
            
            # 4. Export scene as USD (USDA ascii layout for human readable composition verification)
            export_props = bpy.ops.wm.usd_export.get_rna_type().properties
            kwargs = {}
            # Use the "Export Animation" checkbox setting
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
                kwargs["export_materials"] = False
            if "export_subdivision" in export_props:
                kwargs["export_subdivision"] = "BEST_MATCH"
            if "export_armatures" in export_props:
                kwargs["export_armatures"] = True
            if "only_deform_bones" in export_props:
                kwargs["only_deform_bones"] = True
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
            
            # Save a copy of the active .blend file inside the version directory
            if current_blend and os.path.exists(current_blend):
                import shutil
                blend_copy_name = f"{asset_prefix}_v{version:03d}.blend"
                blend_copy_path = os.path.join(version_dir, blend_copy_name)
                try:
                    shutil.copy2(current_blend, blend_copy_path)
                    print(f"[Studio Tools] Exported .blend copy to: {blend_copy_path}")
                except Exception as bce:
                    print(f"[Studio Tools] Warning: Failed to export .blend copy: {bce}")
            
            # 5. Write metadata
            meta_path = os.path.join(version_dir, "metadata.yaml")
            exported_objs = [obj.name for obj in bpy.context.scene.objects if not obj.parent]
            
            meta_data = {
                "type": "usd_publish",
                "application": "blender",
                "application_version": os.environ.get("ST_APP_VERSION") or bpy.app.version_string,
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
                        import shutil
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

# --- File Load/Save handler to set default asset name ---
def update_default_asset_name(dummy1=None, dummy2=None):
    """Automatically updates the default asset name to match the blend file name on load/save."""
    if not IN_BLENDER:
        return
    try:
        current_file = bpy.data.filepath
        if current_file:
            # Only update if it is currently the default "scene"
            scene = bpy.context.scene
            if scene and scene.studiotools_asset_name == "scene":
                blend_name = os.path.splitext(os.path.basename(current_file))[0]
                if blend_name and blend_name != "untitled":
                    clean_name = re.sub(r"[._-]?v\d+$", "", blend_name, flags=re.IGNORECASE)
                    scene.studiotools_asset_name = re.sub(r"[^a-zA-Z0-9_]", "_", clean_name)
    except Exception as e:
        print(f"[Studio Tools] Warning: Failed to update default asset name: {e}")

if IN_BLENDER:
    @bpy.app.handlers.persistent
    def update_default_asset_name_handler(dummy1=None, dummy2=None):
        update_default_asset_name()

# --- Panel UI ---

class VIEW3D_PT_studiotools_pipeline(Panel):
    """Creates a custom side panel in the 3D Viewport sidebar."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Studio Tools'
    bl_label = 'Pipeline Controls'
    
    def draw(self, context):
        layout = self.layout
        
        # Display Context Info
        task = os.environ.get("ST_TASK", "Unknown")
        task_area = os.environ.get("ST_TASKAREA", "Unknown")
        
        box = layout.box()
        box.label(text="Context Information", icon='INFO')
        row = box.row()
        row.label(text=f"Task Area: {task_area}")
        row = box.row()
        row.label(text=f"Task: {task}")
        
        current_file = bpy.data.filepath
        if current_file:
            box.label(text=f"File: {os.path.basename(current_file)}", icon='FILE_BLEND')
        else:
            box.label(text="File: Unsaved Scene", icon='FILE_BLEND')
            
        layout.separator()
        
        box_publish = layout.box()
        box_publish.label(text="USD Export Settings", icon='EXPORT')
        box_publish.prop(context.scene, "studiotools_asset_name", text="Asset Name")
        box_publish.prop(context.scene, "studiotools_export_animation", text="Export Animation")
        box_publish.prop(context.scene, "studiotools_export_usdc", text="Export as USDC (binary cache)")
        box_publish.prop(context.scene, "studiotools_mark_as_published", text="Mark as Published")
        box_publish.operator("wm.studiotools_publish_usd", icon='EXPORT', text="Publish USD Asset")

# --- Registration & Initialization ---

classes = [
    WM_OT_studiotools_load_usd,
    WM_OT_studiotools_publish_usd,
    VIEW3D_PT_studiotools_pipeline
]

def register():
    if not IN_BLENDER:
        return
    
    # Register scene properties
    bpy.types.Scene.studiotools_asset_name = bpy.props.StringProperty(
        name="Asset Name",
        description="Name of the published asset (e.g. character, prop, scene)",
        default="scene"
    )
    bpy.types.Scene.studiotools_mark_as_published = bpy.props.BoolProperty(
        name="Mark as Published",
        description="Create a published symlink in published/ pointing to this version",
        default=True
    )
    bpy.types.Scene.studiotools_export_animation = bpy.props.BoolProperty(
        name="Export Animation",
        description="Export animation frames in the USD file",
        default=False
    )
    bpy.types.Scene.studiotools_export_usdc = bpy.props.BoolProperty(
        name="Export as USDC",
        description="Export as binary USDC instead of human-readable USDA (recommended for heavy caches)",
        default=False
    )

    for cls in classes:
        bpy.utils.register_class(cls)

    # Register handlers
    if update_default_asset_name_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(update_default_asset_name_handler)
    if update_default_asset_name_handler not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(update_default_asset_name_handler)

def unregister():
    if not IN_BLENDER:
        return
        
    # Unregister handlers
    if update_default_asset_name_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(update_default_asset_name_handler)
    if update_default_asset_name_handler in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(update_default_asset_name_handler)

    # Unregister scene properties
    del bpy.types.Scene.studiotools_asset_name
    del bpy.types.Scene.studiotools_mark_as_published
    del bpy.types.Scene.studiotools_export_animation
    del bpy.types.Scene.studiotools_export_usdc

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

def init_blender_scene():
    if not IN_BLENDER:
        return
        
    task_path = os.environ.get("ST_CWD")
    if not task_path:
        print("[Studio Tools] Warning: ST_CWD environment variable not set.")
        return
        
    print("------------------------------------------------------------------")
    print("  [Studio Tools Pipeline] Initializing inside Blender...")
    print("------------------------------------------------------------------")
    
    wip_dir = os.path.join(task_path, "wip")
    app_dir = os.path.join(wip_dir, "blender")
    os.makedirs(app_dir, exist_ok=True)
    
    # Determine latest version
    version = 1
    if os.path.exists(app_dir):
        for f in os.listdir(app_dir):
            match = re.search(r"scene_v(\d+)\.blend", f, re.IGNORECASE)
            if match:
                version = max(version, int(match.group(1)))
                
    file_name = f"scene_v{version:03d}.blend"
    save_path = os.path.abspath(os.path.join(app_dir, file_name))
    
    # Save/Load file
    if not os.path.exists(save_path):
        try:
            bpy.ops.wm.save_as_mainfile(filepath=save_path)
            print(f"[Studio Tools] Created and saved new blank startup scene: {save_path}")
        except Exception as e:
            print(f"[Studio Tools] Failed to save startup BLEND file: {e}")
    else:
        # Load existing file if it's not already loaded
        current_file = os.path.abspath(bpy.data.filepath) if bpy.data.filepath else ""
        if current_file != save_path:
            try:
                bpy.ops.wm.open_mainfile(filepath=save_path)
                print(f"[Studio Tools] Loaded existing version file on startup: {save_path}")
            except Exception as e:
                print(f"[Studio Tools] Failed to load BLEND file: {e}")

    # Update default asset name to match current file name
    update_default_asset_name()



                
    print("------------------------------------------------------------------")
    print("  [Studio Tools Pipeline] Ready!")
    print("------------------------------------------------------------------")

# --- Background Web Connection Loop ---
def poll_web_connection():
    task_path = os.environ.get("ST_CWD")
    if not task_path:
        return 1.0  # Try again in 1s
        
    try:
        import urllib.request
        import urllib.parse
        import json
        
        url = f"http://localhost:8000/api/sessions/poll?appType=blender&taskPath={urllib.parse.quote(task_path)}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=0.2) as response:
            res = json.loads(response.read().decode())
            commands = res.get("commands", [])
            for cmd in commands:
                if cmd.get("command") == "load_usd":
                    filepath = cmd.get("argument")
                    if os.path.exists(filepath):
                        bpy.ops.wm.usd_import(filepath=filepath)
                        print(f"[Studio Tools] Web Connection: Loaded published USD asset: {filepath}")
    except Exception:
        pass  # Safe silence to avoid console spam if server is offline
        
    return 0.5  # Poll every 500ms

# Run registration and load scene files
if __name__ == "__main__":
    register()
    init_blender_scene()
    
    # Start web connection background poll
    if IN_BLENDER:
        try:
            bpy.app.timers.register(poll_web_connection)
            print("[Studio Tools] Web Connection active and listening for load actions...")
        except Exception as e_timer:
            print(f"[Studio Tools] Warning: Failed to register Web Connection background timer: {e_timer}")
