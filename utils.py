import bpy # type: ignore
import os
import re


def get_latest_version():
    filepath = bpy.data.filepath

    if not filepath:
        return 0
    
    wip_folder = os.path.dirname(os.path.dirname(filepath))
    version_pattern = re.compile(r'_v(\d+)$', re.IGNORECASE)
    
    max_version = 0
    
    for app_folder in os.listdir(wip_folder):
        app_folder_path = os.path.join(wip_folder, app_folder)
        
        if not os.path.isdir(app_folder_path):
            continue
        
        for app in os.listdir(os.path.join(wip_folder, app_folder)):
            name, ext = os.path.splitext(app)
            match = version_pattern.search(name)
            if match:
                ver = int(match.group(1))
                if ver > max_version:
                    max_version = ver
            # check for _v***
            # return the newest version
            
    return max_version

def save_version():
    filepath = bpy.data.filepath
    base_path, ext = os.path.splitext(filepath)
    base_name = os.path.basename(base_path).split("_v")[0]
    
    latest_version = get_latest_version()
    next_version = latest_version + 1
        
    new_base = os.path.join(os.path.dirname(base_path), f"{base_name}_v{next_version:03d}")
    new_filepath = f"{new_base}{ext}"
    bpy.ops.wm.save_as_mainfile(filepath=new_filepath, compress=True)

def get_current_version():
    filepath = bpy.data.filepath
    if not filepath:
        return 0

    base_path = os.path.splitext(os.path.basename(filepath))[0]  # just the filename without extension
    version_match = re.search(r'_v(\d+)$', base_path)
    if version_match:
        return int(version_match.group(1))
    
    return 0

def get_all_objects_from_collection(collection, include_children=True):
    objects = []
    objects.extend(collection.objects)
    if include_children:
        for child_collection in collection.children:
            objects.extend(get_all_objects_from_collection(child_collection, include_children=True))
    return objects


def data_from_root_collection(root_collection):
    # Get all objects (including nested collections)
    all_objects = get_all_objects_from_collection(root_collection)

    # Gather all data blocks (objects, meshes, materials, etc.)
    data_blocks = set()
    # 1. Add the main collection and its children (if needed)
    data_blocks.add(root_collection)
        
    # Optional: Add all child collections recursively
    def add_collections_recursive(collection):
        for child in collection.children:
            data_blocks.add(child)
            add_collections_recursive(child)
    
    add_collections_recursive(root_collection)

    for obj in all_objects:
        data_blocks.add(obj)
        if obj.data:
            data_blocks.add(obj.data)
        if hasattr(obj.data, 'materials'):
            for mat in obj.data.materials:
                if mat:
                    data_blocks.add(mat)

    return data_blocks

def show_popup(title="Popup", text="", icon="INFO"):
    def draw(self, context):
        self.layout.label(text=text)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def set_primvar(item, primvar, value, override=False):
    if primvar in item and not override:
        return
    item[primvar] = value

def get_primvar(item, primvar, default):    
    if primvar in item:
        return item[primvar]

    return default

def remove_primvar(item, primvar):
    if primvar in item:
        del item[primvar]        

def check_primvar(item, primvar):
    return primvar in item

def validate_primvar(item, primvar, value):
    """Check if a Blender object has a matching primvar value in its custom properties.
    
    Args:
        item (bpy.types.Object): Blender object to check
        primvar (dict): Primvar specification with "name" and "value" keys
    
    Returns:
        bool: True if object has the primvar property and values match
    """
    if primvar not in item:
        return False
    
    # Compare values - handle Blender ID properties correctly
    return item[primvar] == value
