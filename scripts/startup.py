import os
import sys
import re

# Add scripts directory to sys.path so we can import our modules
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.append(_this_dir)

try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

import utils
import operators
import handlers
import ui
import connection

# List of classes to register
classes = [
    operators.WM_OT_studiotools_unlink_asset,
    operators.WM_OT_studiotools_new_file,
    operators.WM_OT_studiotools_increment_save,
    operators.WM_OT_studiotools_link_asset,
    operators.WM_OT_studiotools_swap_version,
    operators.WM_OT_studiotools_load_usd,
    operators.WM_OT_studiotools_publish_usd,
    operators.WM_OT_studiotools_render_still,
    operators.WM_OT_studiotools_render_sequence,
    operators.WM_OT_studiotools_render_playblast,
    ui.VIEW3D_PT_studiotools_pipeline
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
    bpy.types.Scene.studiotools_import_path = bpy.props.StringProperty(
        name="Import Folder Path",
        description="Paste the copied asset/version folder path to link it",
        default=""
    )
    bpy.types.Scene.studiotools_render_name = bpy.props.StringProperty(
        name="Render Name",
        description="Name of the output render sequence",
        default="render"
    )

    for cls in classes:
        bpy.utils.register_class(cls)

    # Register handlers
    if handlers.update_default_asset_name_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(handlers.update_default_asset_name_handler)
    if handlers.update_default_asset_name_handler not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(handlers.update_default_asset_name_handler)
    if handlers.sync_materials_viewport_color not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(handlers.sync_materials_viewport_color)

def unregister():
    if not IN_BLENDER:
        return
        
    # Unregister handlers
    if handlers.update_default_asset_name_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(handlers.update_default_asset_name_handler)
    if handlers.update_default_asset_name_handler in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(handlers.update_default_asset_name_handler)
    if handlers.sync_materials_viewport_color in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(handlers.sync_materials_viewport_color)

    # Unregister scene properties
    del bpy.types.Scene.studiotools_asset_name
    del bpy.types.Scene.studiotools_mark_as_published
    del bpy.types.Scene.studiotools_export_animation
    del bpy.types.Scene.studiotools_export_usdc
    del bpy.types.Scene.studiotools_import_path
    del bpy.types.Scene.studiotools_render_name

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
    
    preload_file = os.environ.get("ST_PRELOAD_FILE")
    if preload_file:
        save_path = os.path.abspath(preload_file)
        print(f"[Studio Tools] Using preload file from environment: {save_path}")
    else:
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
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
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

    # Update default asset name and render name to match current file name
    utils.update_default_asset_name()
    utils.update_default_render_name()
                
    print("------------------------------------------------------------------")
    print("  [Studio Tools Pipeline] Ready!")
    print("------------------------------------------------------------------")

if __name__ == "__main__":
    register()
    init_blender_scene()
    
    # Start web connection background poll
    if IN_BLENDER:
        try:
            bpy.app.timers.register(connection.poll_web_connection)
            print("[Studio Tools] Web Connection active and listening for load actions...")
        except Exception as e_timer:
            print(f"[Studio Tools] Warning: Failed to register Web Connection background timer: {e_timer}")
