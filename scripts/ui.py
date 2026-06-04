import os
import re
import utils

try:
    import bpy
    from bpy.types import Panel
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False
    class Panel:
        pass


class VIEW3D_PT_studiotools_pipeline(Panel):
    """Creates a custom side panel in the 3D Viewport sidebar."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Studio Tools'
    bl_label = 'Pipeline Controls'
    
    def draw(self, context):
        if not IN_BLENDER:
            return
            
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
            
        row_btns = box.row(align=True)
        row_btns.operator("wm.studiotools_increment_save", text="Increment Save", icon='DUPLICATE')
        row_btns.operator("wm.studiotools_new_file", text="New Empty", icon='FILE_NEW')
            
        layout.separator()
        
        # Link Asset Panel
        box_link = layout.box()
        box_link.label(text="Link Project Asset", icon='LINKED')
        box_link.prop(context.scene, "studiotools_import_path", text="Path")
        box_link.operator("wm.studiotools_link_asset", text="Link Asset", icon='APPEND_BLEND')

        # Linked Asset HUD
        has_linked_assets = False
        for lib in bpy.data.libraries:
            # We ONLY draw libraries that were directly linked by StudioTools
            if not lib.get("studiotools_direct", False):
                continue
                
            # Resolve symlink path to find real asset/version folder on disk for HUD version logic
            norm_path = os.path.abspath(bpy.path.abspath(lib.filepath))
            real_path = os.path.realpath(norm_path)
            
            if "versions" in real_path and real_path.endswith("scene.blend"):
                if not has_linked_assets:
                    has_linked_assets = True
                    layout.separator()
                    layout.label(text="Linked Assets HUD", icon='LINKED')
                
                box_hud = layout.box()
                lib_dir = os.path.dirname(real_path)
                asset_dir = os.path.dirname(lib_dir)
                asset_name = os.path.basename(asset_dir)
                current_ver = os.path.basename(lib_dir)
                
                # Check if the active linked path is the published symlink path
                is_published_link = "published" in norm_path
                
                row = box_hud.row(align=True)
                row.label(text=f"{asset_name}", icon='FILE_BLEND')
                if is_published_link:
                    row.label(text="Active: published", icon='CHECKMARK')
                else:
                    row.label(text=f"Active: {current_ver}", icon='CHECKMARK')
                    
                op_unlink = row.operator("wm.studiotools_unlink_asset", text="", icon='REMOVE')
                op_unlink.library_name = lib.name
                
                # Scan other versions on disk
                if os.path.exists(asset_dir):
                    versions = sorted([
                        d for d in os.listdir(asset_dir)
                        if os.path.isdir(os.path.join(asset_dir, d)) and re.match(r"^v\d+$", d)
                    ])
                    if versions:
                        row_vers = box_hud.row(align=True)
                        for ver in versions:
                            is_active = (ver == current_ver) and not is_published_link
                            icon_style = 'RADIOBUT_ON' if is_active else 'RADIOBUT_OFF'
                            op = row_vers.operator("wm.studiotools_swap_version", text=ver, icon=icon_style)
                            op.library_name = lib.name
                            op.target_version = ver

        # Render Sequence Setup
        box_render = layout.box()
        box_render.label(text="Render Sequence Setup", icon='RENDER_ANIMATION')
        box_render.prop(context.scene, "studiotools_render_name", text="Render Name")
        
        # Display resolved filepath preview so the artist knows where it goes
        scene = context.scene
        task_path = os.environ.get("ST_CWD")
        if task_path:
            render_name = scene.studiotools_render_name.strip() or "render"
            
            # Calculate dynamic output path previews using utils helper
            exr_ver, exr_dir, exr_file, _ = utils.get_render_version_and_paths(task_path, render_name, 'exr', create_dirs=False)
            pb_ver, pb_dir, pb_file, _ = utils.get_render_version_and_paths(task_path, render_name, 'playblast', create_dirs=False)
            
            # EXR Preview
            box_render.label(text=f"Next Render: v{exr_ver:03d}", icon='FILE_NEW')
            col_preview = box_render.column(align=True)
            col_preview.scale_y = 0.8
            col_preview.label(text=f"Dir: versions/{os.path.basename(os.path.dirname(exr_dir))}/{os.path.basename(exr_dir)}/")
            col_preview.label(text=f"File: {exr_file}")
            
            box_render.separator()
            
            # Playblast Preview
            box_render.label(text=f"Next Playblast: v{pb_ver:03d}", icon='FILE_NEW')
            col_pb_preview = box_render.column(align=True)
            col_pb_preview.scale_y = 0.8
            col_pb_preview.label(text=f"Dir: versions/{os.path.basename(os.path.dirname(pb_dir))}/{os.path.basename(pb_dir)}/")
            col_pb_preview.label(text=f"File: {pb_file}")
            
            box_render.separator()

        col_btns = box_render.column(align=True)
        col_btns.operator("wm.studiotools_render_still", text="Render Still Frame", icon='RENDER_STILL')
        col_btns.operator("wm.studiotools_render_sequence", text="Render Animation", icon='RENDER_ANIMATION')
        col_btns.operator("wm.studiotools_render_playblast", text="Render Playblast (Preview)", icon='CAMERA_STEREO')


        layout.separator()
        
        box_publish = layout.box()
        box_publish.label(text="USD Export Settings", icon='EXPORT')
        box_publish.prop(context.scene, "studiotools_asset_name", text="Asset Name")
        box_publish.prop(context.scene, "studiotools_export_animation", text="Export Animation")
        box_publish.prop(context.scene, "studiotools_export_usdc", text="Export as USDC (binary cache)")
        box_publish.prop(context.scene, "studiotools_mark_as_published", text="Mark as Published")
        box_publish.operator("wm.studiotools_publish_usd", icon='EXPORT', text="Publish USD Asset")
