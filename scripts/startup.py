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
    
    asset_name: StringProperty(
        name="Asset Name",
        description="Name of the published asset (e.g. character, prop, scene)",
        default="scene"
    )
    
    def invoke(self, context, event):
        # Default to current Blend file name (sans extension)
        blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else ""
        if blend_name and blend_name != "untitled":
            # Strip version suffix (e.g. _v001 or _v1) from default asset name prompt
            clean_name = re.sub(r"_v\d+$", "", blend_name, flags=re.IGNORECASE)
            # Clean name for filesystem safety
            self.asset_name = re.sub(r"[^a-zA-Z0-9_]", "_", clean_name)
        else:
            self.asset_name = "scene"
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        task_path = os.environ.get("ST_CWD")
        if not task_path:
            self.report({'ERROR'}, "ST_CWD environment variable not set.")
            return {'CANCELLED'}
            
        try:
            # 1. Save active Blend file
            bpy.ops.wm.save_mainfile()
            current_blend = bpy.data.filepath
            
            # 2. Determine published directory packaged in a folder
            published_dir = os.path.join(task_path, "published")
            os.makedirs(published_dir, exist_ok=True)
            
            # 3. Determine next version by scanning directory folders
            version = 1
            asset_prefix = self.asset_name.strip()
            if not asset_prefix:
                asset_prefix = "scene"
            # Strip any version suffix (e.g. _v001, -v1, v3) entered by the user
            asset_prefix = re.sub(r"[._-]?v\d+$", "", asset_prefix, flags=re.IGNORECASE)
            asset_prefix = re.sub(r"[^a-zA-Z0-9_]", "_", asset_prefix)
            
            if os.path.exists(published_dir):
                for f in os.listdir(published_dir):
                    if os.path.isdir(os.path.join(published_dir, f)):
                        match = re.search(rf"^{re.escape(asset_prefix)}_v(\d+)", f, re.IGNORECASE)
                        if match:
                            version = max(version, int(match.group(1)) + 1)
                        
            version_folder = f"{asset_prefix}_v{version:03d}"
            version_dir = os.path.join(published_dir, version_folder)
            os.makedirs(version_dir, exist_ok=True)
            
            pub_filename = f"{asset_prefix}_v{version:03d}.usda"
            pub_filepath = os.path.join(version_dir, pub_filename)
            
            # 4. Export scene as USD (USDA ascii layout for human readable composition verification)
            # Query accepted export properties to avoid unrecognized keyword errors across Blender versions,
            # dynamically excluding the World background, lights, and cameras if supported.
            export_props = bpy.ops.wm.usd_export.get_rna_type().properties
            kwargs = {}
            if "export_world" in export_props:
                kwargs["export_world"] = False
            if "export_lights" in export_props:
                kwargs["export_lights"] = False
            if "export_cameras" in export_props:
                kwargs["export_cameras"] = False
                
            bpy.ops.wm.usd_export(filepath=pub_filepath, **kwargs)
            
            # 5. Write metadata
            meta_path = os.path.join(version_dir, "metadata.yaml")
            exported_objs = [obj.name for obj in bpy.context.scene.objects if not obj.parent]
            
            meta_data = {
                "type": "usd_publish",
                "application": "blender",
                "application_version": bpy.app.version_string,
                "source_file": os.path.basename(current_blend) if current_blend else "unsaved.blend",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": os.environ.get("USER", "artist"),
                "exported_root_objects": exported_objs
            }
            write_simple_yaml(meta_path, meta_data)
            
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
        
        # Load & Publish Buttons
        col = layout.column(align=True)
        col.operator("wm.studiotools_load_usd", icon='IMPORT', text="Load USD Asset...")
        col.separator()
        col.operator("wm.studiotools_publish_usd", icon='EXPORT', text="Publish USD Asset...")

# --- Registration & Initialization ---

classes = [
    WM_OT_studiotools_load_usd,
    WM_OT_studiotools_publish_usd,
    VIEW3D_PT_studiotools_pipeline
]

def register():
    if not IN_BLENDER:
        return
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    if not IN_BLENDER:
        return
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
