import bpy # type: ignore
import bmesh # type: ignore
import random
import re
import hashlib
from .. import utils

def color_from_tag(tag_name):
    """Generate a deterministic RGB color from a tag name."""
    h = hashlib.md5(tag_name.encode("utf-8")).hexdigest()
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b, 1.0)  # RGBA

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
            if (utils.check_primvar(obj, "shaderTag")):
                tag_name = utils.get_primvar(obj, "shaderTag", "default")
                if not any(tag_name == tag.name for tag in shader_tags):
                    tag = shader_tags.add()
                    tag.name = tag_name

    for tag in shader_tags:
        material_name = tag.name + "_SHD"

        material = bpy.data.materials.get(material_name)

        if not material:
            material = bpy.data.materials.new(name=material_name)
            material.use_nodes = True
            
            material.diffuse_color = color_from_tag(tag.name)

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
            tag_name = utils.get_primvar(obj, "shaderTag", None)
            
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

def rename(objects):
    studiotools_asset = bpy.context.scene.studiotools_asset
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
        result, data = validate_name(obj.name)
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

def validate(objects):
    num_errors = 0
    num_warnings = 0

    print("\nValidating Objects...\n")
    for obj in objects:
        validation_error_prefix = f"ERROR ({obj.name}):"
        validation_warning_prefix = f"WARNING ({obj.name})"
        result, data = validate_name(obj.name)
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
        return False, num_errors, num_warnings
    else:
        print("Validation: PASSED")
        print(f"Objects Checked: {len(objects)}")
        print(f"Warnings: {num_warnings}")
        return True, num_errors, num_warnings