import os
import re

try:
    import bpy
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

def resolve_blend_path(input_path):
    input_path = input_path.strip()
    if not input_path:
        return None, None
        
    # We do NOT resolve symlinks here so we link the exact path the user gave (e.g. published/scene)
    abs_path = os.path.abspath(input_path)
    
    # 1. If it's a file ending in .blend, check if it exists
    if os.path.isfile(abs_path) and abs_path.endswith(".blend"):
        return abs_path, os.path.dirname(abs_path)
        
    # 2. If it's a folder, search for scene.blend inside it
    if os.path.isdir(abs_path):
        candidate = os.path.join(abs_path, "scene.blend")
        if os.path.exists(candidate):
            return candidate, abs_path
            
        # 3. If it doesn't contain scene.blend directly, it might be the asset folder (which contains v001, v002...)
        # Find the latest version folder (we resolve the path only to read its version directories on disk)
        real_path = os.path.realpath(abs_path)
        versions = sorted([
            d for d in os.listdir(real_path)
            if os.path.isdir(os.path.join(real_path, d)) and re.match(r"^v\d+$", d)
        ])
        if versions:
            latest_ver_dir = os.path.join(real_path, versions[-1])
            candidate = os.path.join(latest_ver_dir, "scene.blend")
            if os.path.exists(candidate):
                # Return the unresolved path with the latest version folder appended
                unresolved_candidate = os.path.join(abs_path, versions[-1], "scene.blend")
                return unresolved_candidate, os.path.join(abs_path, versions[-1])

    return None, None

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

def update_default_render_name(dummy1=None, dummy2=None):
    """Automatically updates the default render name to match the blend file name on load/save."""
    if not IN_BLENDER:
        return
    try:
        current_file = bpy.data.filepath
        if current_file:
            # Only update if it is currently the default "render"
            scene = bpy.context.scene
            if scene and scene.studiotools_render_name == "render":
                blend_name = os.path.splitext(os.path.basename(current_file))[0]
                if blend_name and blend_name != "untitled":
                    clean_name = re.sub(r"[._-]?v\d+$", "", blend_name, flags=re.IGNORECASE)
                    scene.studiotools_render_name = re.sub(r"[^a-zA-Z0-9_]", "_", clean_name)
    except Exception as e:
        print(f"[Studio Tools] Warning: Failed to update default render name: {e}")

def get_render_version_and_paths(task_path, render_name, render_type, create_dirs=False):
    """
    Computes version and directories/filenames for rendering.
    render_type: 'exr' or 'playblast'
    Returns: (version, version_dir, filename, filepath)
    """
    # Strip illegal characters
    render_name = re.sub(r"[^a-zA-Z0-9_]", "_", render_name)
    if render_type == "playblast":
        folder_name = f"{render_name}_playblast"
        filename_pattern = f"{render_name}_playblast_v{{version:03d}}_####.jpg"
    else:
        folder_name = render_name
        filename_pattern = f"{render_name}_v{{version:03d}}_####.exr"

    versions_dir = os.path.join(task_path, "versions", folder_name)
    if create_dirs:
        os.makedirs(versions_dir, exist_ok=True)

    version = 1
    if os.path.exists(versions_dir):
        for f in os.listdir(versions_dir):
            if os.path.isdir(os.path.join(versions_dir, f)):
                match = re.match(r"^v(\d+)", f, re.IGNORECASE)
                if match:
                    version = max(version, int(match.group(1)) + 1)

    version_dir = os.path.join(versions_dir, f"v{version:03d}")
    if create_dirs:
        os.makedirs(version_dir, exist_ok=True)

    filename = filename_pattern.format(version=version)
    filepath = os.path.abspath(os.path.join(version_dir, filename))

    return version, version_dir, filename, filepath

def setup_render_settings(scene, render_type, filepath):
    """
    Configures Blender's scene.render settings based on render_type ('exr' or 'playblast')
    and sets the output filepath.
    """
    scene.render.filepath = filepath
    
    if render_type == 'playblast':
        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.quality = 90
    else:
        # Check supported formats to dynamically handle OPEN_EXR
        prop = scene.render.image_settings.bl_rna.properties['file_format']
        supported_formats = {item.identifier for item in prop.enum_items}
        
        if'OPEN_EXR' in supported_formats:
            scene.render.image_settings.file_format = 'OPEN_EXR'
        else:
            scene.render.image_settings.file_format = 'PNG'  # Fallback
            
        # Configure color depth and compression if format is EXR
        if scene.render.image_settings.file_format in ('OPEN_EXR'):
            scene.render.image_settings.color_depth = '16'
            scene.render.image_settings.exr_codec = 'DWAA'

