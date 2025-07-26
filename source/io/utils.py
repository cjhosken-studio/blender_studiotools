import json
from datetime import datetime
import os
import platform
import getpass
import bpy

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