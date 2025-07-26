import json
from datetime import datetime
import os
import platform
import getpass
import bpy
import random
import re

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

def write_metadata(filepath, context):
    filedir = os.path.abspath(os.path.dirname(filepath))

    studiotools_io = context.scene.studiotools_io
    asset_path = os.path.abspath(studiotools_io.export_path)
    version = studiotools_io.export_version

    metadata = {
        "name": os.path.basename(os.path.dirname(asset_path)),
        "asset_url": filedir,
        "version": f"{version:03d}",
        "thumbnail": os.path.join(filedir, "thumbnail.png"),
        "timestamp": datetime.now().isoformat(),
        "system": {
            "os":platform.system(),
            "user":getpass.getuser(),
            "dcc":"blender",
            "dcc_version":bpy.app.version_string
        },
        "files": [
            path for path in os.listdir(filedir)
        ]
    }

    with open(filepath, "w") as f:
        json.dump(metadata, f, indent=4)

def show_popup(title="Popup", text="", icon="INFO"):
    def draw(self, context):
        self.layout.label(text=text)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def validate_name(name):
    """
    Validate if a filename follows the {pos}_{name}_{variant}_{ext} pattern.
    
    Args:
        name (str): Filename to validate
        
    Returns:
        tuple: (bool, str) - (True if valid, error message if invalid)
    """
    if not name:
        return False, "Empty filename"
    
    # Basic pattern check (allowing alphanumeric and some special chars)
    pattern = r'^[a-zA-Z0-9]+_[a-zA-Z0-9]+_[a-zA-Z0-9]+_[a-zA-Z0-9]'
    
    if not re.match(pattern, name):
        return False, "Name doesn't match {pos}_{name}_{variant}_{ext} pattern."
    
    # Check for exactly 3 underscores (4 components)
    if name.count('_') != 3:
        return False, "Name should contain exactly 3 underscores."
    
    # Split into components
    try:
        pos, asset_name, variant, ext = name.split('_')
        ext = ext.split('.')[-1]  # Get extension after last dot
    except ValueError:
        return False, "Couldn't parse name components."
    
    # Validate position code (example: L, R, C, etc.)
    if not pos or len(pos) > 3:
        return False, "Name position code should be 1-3 characters."
    
    # Validate variant
    if not variant:
        return False, "Name is missing variant."
    
    # Validate extension
    valid_extensions = {
        "GEP", # mesh
        "GES", # subdivided mesh
        "PLY", # non-renderable mesh
        "CAM", # camera
        "LGT", # light / light probe
        "TXT", # text
        "VOL", # volume
        "GSP", # grease pencil
        "LOC", # empty / force field
        "IMG", # image
        "AUD", # speaker
        "RIG", # armature
        "LAT", # lattice
        "CRV", # curve
        "NRB", # surface / metaball
        "UNK" # unknown
    }
    if ext not in valid_extensions:
        return False, f"Name has an invalid extension. Allowed: {', '.join(valid_extensions)}"
    
    return True, [pos, asset_name, variant, ext]

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

def find_unique_name(base_name, existing_names, padding=4):
    """Generate a unique name by appending numbers if needed"""
    if base_name not in existing_names:
        return base_name
        
    # Find the highest existing number
    max_num = 0
    for name in existing_names:
        if name.startswith(base_name):
            suffix = name[len(base_name):]
            if suffix.startswith('_'):
                try:
                    num = int(suffix[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
    
    return f"{base_name}_{max_num + 1:0{padding}d}"

def refresh_shader_tags(context):
    studiotools_asset = context.scene.studiotools_asset
    shader_tags = studiotools_asset.shader_tags

    for obj in bpy.data.objects:
        if obj.type == "MESH":
            if (check_primvar(obj, "shaderTag")):
                tag_name = get_primvar(obj, "shaderTag", "default")
                if not any(tag_name == tag.name for tag in shader_tags):
                    tag = shader_tags.add()
                    tag.name = tag_name

    for tag in shader_tags:
        material_name = tag.name + "_SHD"

        material = bpy.data.materials.get(material_name)

        if not material:
            material = bpy.data.materials.new(name=material_name)
            material.use_nodes = True

            r = random.uniform(0.2, 1.0)
            g = random.uniform(0.2, 1.0)
            b = random.uniform(0.2, 1.0)
            
            material.diffuse_color = (r, g, b, 1.0)

    for material in bpy.data.materials:
        material_name = material.name
        if material_name.endswith("_SHD"):
            material_tag_name = material_name.replace("_SHD", "")

            if not any(material_tag_name == tag.name for tag in shader_tags):
                material = bpy.data.materials[material_name]
                if material:
                    for obj in bpy.data.objects:
                        for slot in obj.material_slots:
                            if slot.material == material:
                                slot.material = None

                bpy.data.materials.remove(material)


    for obj in bpy.data.objects:
        if obj.type == "MESH":
            # Get the shaderTag primvar if it exists
            tag_name = get_primvar(obj, "shaderTag", None)
            
            if tag_name is not None:
                material_name = f"{tag_name}_SHD"
                
                # Check if material exists
                if material_name in bpy.data.materials:
                    material = bpy.data.materials[material_name]
                    
                    # Ensure object has at least one material slot
                    if not obj.material_slots:
                        obj.data.materials.append(material)
                    else:
                        # Assign to first material slot
                        obj.material_slots[0].material = material
                else:
                    print(f"Warning: Material {material_name} not found for object {obj.name}")
