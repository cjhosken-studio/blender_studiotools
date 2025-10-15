import bpy # type: ignore
import os
import yaml
from . import utils

def export_usd(filepath="./stage.usd", root_collection=None, export_asset=False, export_animation=False, include_materials=False, include_rigs=False, pack_textures=False):    
    bpy.context.scene.frame_current = bpy.context.scene.frame_start

    objects = utils.get_all_objects_from_collection(root_collection)

    for obj in objects:
        if obj.type in ["MESH", "CURVE", "POINTCLOUD", "SURFACE"]:
            utils.set_primvar(obj, "Pref", [v.co for v in obj.data.vertices])

    bpy.ops.wm.usd_export(
        filepath=filepath,
        collection=root_collection.name,
        export_meshes=export_asset or export_animation,
        export_lights=True,
        export_cameras=export_animation,
        export_volumes=True,
        export_curves=True,
        export_hair=True,
        export_subdivision="BEST_MATCH",
        export_uvmaps=True,
        rename_uvmaps=True,
        export_animation=export_animation,
        export_materials=include_materials,
        generate_preview_surface=include_materials,
        export_textures=include_materials,
        overwrite_textures=True,
        export_textures_mode="NEW" if pack_textures else "KEEP",
        relative_paths=True,
        merge_parent_xform=True,
        export_custom_properties=True,
        custom_properties_namespace="",
        author_blender_name=False,
        convert_world_material=False,
        convert_scene_units="METERS",
        meters_per_unit=1.0,
        convert_orientation=True,
        export_armatures=include_rigs,
        export_shapekeys=include_rigs,
        only_deform_bones=include_rigs,
        use_instancing=True
    )

    for obj in objects:
        utils.remove_primvar(obj, "Pref")
    
    return True
    
def export_blend(filepath="./scene.blend", root_collection=None):

    data_blocks = utils.data_from_root_collection(root_collection)

    bpy.data.libraries.write(
        filepath=filepath,
        datablocks=data_blocks,
        fake_user=True,
        compress=True
    )
    
    return True

def export(filepath="./", root_collection=None, export_asset=False, export_animation=False, thumbnail=True):
    if root_collection:
        usd_path = os.path.join(os.path.abspath(filepath), "stage.usd")
        success = export_usd(filepath=usd_path, root_collection=root_collection, export_asset=export_asset, export_animation=export_animation)
        if success:
            success = export_blend(filepath=os.path.join(os.path.abspath(filepath), "scene.blend"), root_collection=root_collection)
        
        if success:
            if thumbnail:
                tmp_filepath = bpy.context.scene.render.filepath

                bpy.context.scene.render.filepath = os.path.join(filepath, "thumbnail.png")
            
                bpy.ops.render.opengl(
                    animation=False,
                    render_keyed_only=False,
                    sequencer=False,
                    write_still=True,
                    view_context=True
                )

                bpy.context.scene.render.filepath = tmp_filepath
                        
            metadata = {
                "root": usd_path,
                "type": "usd",
                "version": utils.get_current_version()
            }
            
            with open(os.path.join(os.path.abspath(filepath), "metadata.yaml"), "w") as f:
                yaml.safe_dump(metadata, f, sort_keys=False)

            return True

    else:
        utils.show_popup("Export Error!", "No root collection! Please specify a root collection.", "ERROR")

    return False