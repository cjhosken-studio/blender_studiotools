import os
import re
import bpy
from .. import utils
from bpy_extras.io_utils import ImportHelper
import json

class STUDIOTOOLS_IO_OT_Export(bpy.types.Operator):
    """Test"""
    bl_idname = "studiotools_io.export"
    bl_label = "Export"

    @classmethod
    def poll(cls, context):
        return context.scene.studiotools.selected_collection and (context.scene.studiotools_io.export_usd or context.scene.studiotools_io.export_blend)

    def execute(self, context):
        scene = context.scene

        studiotools = scene.studiotools
        studiotools_io = scene.studiotools_io

        # Process the filepath


        asset_folder = f"{studiotools_io.asset_name}_v{studiotools_io.export_version:03d}"
        filepath = os.path.join(studiotools_io.export_path, asset_folder)

        if (studiotools_io.export_usd):
            usd_filepath = os.path.join(filepath, f"stage.{studiotools_io.export_usd_type.lower()}")


            objects = utils.get_all_objects_from_collection(studiotools.selected_collection)
            for obj in objects:
                # Add version property if it doesn't exist
                utils.set_primvar(obj, "version", f"{studiotools_io.export_version:03d}")
                utils.set_primvar(obj, "url", os.path.abspath(usd_filepath))
                
                if obj.type == 'MESH':
                    subdiv_mods = [mod for mod in obj.modifiers if mod.type == 'SUBSURF']
                    if subdiv_mods or "_GES" in obj.name:
                        # Calculate combined levels
                        total_viewport = 1
                        total_render = 1
                        subdiv_type = "CATMULL_CLARK"
                        for mod in subdiv_mods:
                            total_viewport *= mod.levels
                            total_render *= mod.render_levels
                            subdiv_type = mod.subdivision_type
                        
                        subdiv_levels = max(total_viewport, total_render)

                        subdiv_type = "catmullClark" if subdiv_type == "CATMULL_CLARK" else "loop"
                        
                        utils.set_primvar(obj, "subdivisionLevels", subdiv_levels)

            bpy.ops.wm.usd_export(
                filepath=usd_filepath,
                check_existing=False,
                collection=studiotools.selected_collection.name,

                export_meshes=studiotools_io.export_usd_meshes,
                export_lights=studiotools_io.export_usd_lights,
                export_cameras=studiotools_io.export_usd_cameras,
                export_points=studiotools_io.export_usd_points,
                export_volumes=studiotools_io.export_usd_volumes,
                export_curves=studiotools_io.export_usd_curves,
                export_hair=studiotools_io.export_usd_curves,

                export_animation=studiotools_io.export_usd_animation,
                export_subdivision="BEST_MATCH",

                export_mesh_colors=studiotools_io.export_usd_relative,

                export_uvmaps=True,
                rename_uvmaps=True,

                export_materials=studiotools_io.export_usd_materials,
                generate_preview_surface=studiotools_io.export_usd_materials_usd,
                generate_materialx_network=studiotools_io.export_usd_materials_mtlx,
                export_textures=True,
                overwrite_textures=True,
                export_textures_mode=studiotools_io.export_usd_textures_mode,
                usdz_downscale_size=studiotools_io.export_usd_textures_usdz_mode,
                usdz_downscale_custom_size=studiotools_io.export_usd_textures_usdz_size,

                relative_paths=False,
                merge_parent_xform=True,

                export_custom_properties=True,
                custom_properties_namespace="",
                author_blender_name=False,

                convert_world_material=False,

                convert_scene_units="METERS",
                meters_per_unit=1.0,
                convert_orientation=True,

                export_armatures=studiotools_io.export_usd_rigs,
                export_shapekeys=studiotools_io.export_usd_rigs,
                only_deform_bones=False,

                use_instancing=True,
                evaluation_mode="RENDER"
            )

            for obj in objects:
                utils.remove_primvar(obj, "version")
                utils.remove_primvar(obj, "url")
                utils.remove_primvar(obj, "subdivisionLevels")

        if (studiotools_io.export_blend):
            blend_filepath = os.path.join(filepath, "scene.blend")

            data_blocks = utils.data_from_root_collection(studiotools.selected_collection)

            objects = utils.get_all_objects_from_collection(studiotools.selected_collection)
            for obj in objects:
                # Add version property if it doesn't exist
                if "version" not in obj:
                    obj["version"] = f"{studiotools_io.export_version:03d}"  # Set default version to 1
                
                # Add source_path property if it doesn't exist
                if "url" not in obj:
                    # You might want to set this to something meaningful, like the original file path
                    obj["url"] = os.path.abspath(blend_filepath)

            bpy.data.libraries.write(
                filepath=blend_filepath, 
                datablocks=data_blocks, 
                fake_user=True,
                compress=True    
            )

            for obj in objects:
                utils.remove_primvar(obj, "version")
                utils.remove_primvar(obj, "url")

        tmp_filepath = context.scene.render.filepath

        context.scene.render.filepath = os.path.join(filepath, "thumbnail.png")
        
        bpy.ops.render.opengl(
            animation=False,
            render_keyed_only=False,
            sequencer=False,
            write_still=True,
            view_context=True
        )

        context.scene.render.filepath = tmp_filepath

        utils.write_metadata(os.path.join(filepath, "metadata.json"), context)

        self.report({"INFO"}, "Export Complete!")
        utils.show_popup("Export Complete!", f"Exported to: {os.path.abspath(filepath)}")

        return {"FINISHED"}
        

# Import Manager Stuff

class STUDIOTOOLS_IO_OT_AddImportItem(bpy.types.Operator):
    bl_idname = "studiotools_io.add_import_item"
    bl_label = "Add Import Item"
    bl_description = "Add a new import item and select file"
    
    # File dialog properties
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(
        default="*.usd;*.usdc;*.usda;*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.exr;*.hdr;*.blend",
        options={'HIDDEN'}
    )
    
    def invoke(self, context, event):
        # Open file browser
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        scene = context.scene
        
        # Add new item
        item = scene.studiotools_io.import_items.add()
        item.path = self.filepath
        
        # Set type based on file extension
        file_ext = self.filepath.lower().split('.')[-1]
        if file_ext in {'usd', 'usdc', 'usda'}:
            item.type = "USD"
        elif file_ext in {'png', 'jpg', 'jpeg', 'tif', 'tiff', 'exr', 'hdr'}:
            item.type = "TEX"
        elif file_ext == 'blend':
            item.type = "LINK"
        else:
            item.type = "NONE"
        
        # Set name from filename
        item.name = os.path.basename(os.path.dirname(self.filepath))
        scene.studiotools_io.active_item_index = len(scene.studiotools_io.import_items) - 1


        return self.add_asset_to_scene(context, item)
    
    
    def add_asset_to_scene(self, context, item):
        metadata_path = os.path.join(os.path.dirname(item.path), "metadata.json")
        metadata = {}
        with open(metadata_path) as f:
            metadata = json.load(f)

        try:
            if (item.type == "TEX"):
                for img in bpy.data.images:
                    if img.filepath == item.path:
                        return

                bpy.data.images.load(item.path)

            elif item.type == "LINK":
                # Get all collections from the blend file
                with bpy.data.libraries.load(item.path, link=False) as (data_from, _):
                    # Link just the first collection found
                    collection_to_link = data_from.collections[0]
                    
                # Now actually link it
                with bpy.data.libraries.load(item.path, link=True) as (_, data_to):
                    data_to.collections = [collection_to_link]
                
                # Add the linked collection to the current scene
                for coll in data_to.collections:
                    if coll and not coll.users:  # Check if not already linked
                        context.scene.collection.children.link(coll)
                        if item.name:  # Use custom name if provided
                            coll.name = item.name
                        return {'FINISHED'}

            elif(item.type == "USD"):

                new_collection_name = re.sub(r'_v\d+$', '', item.name)
                
                bpy.ops.wm.usd_import(
                    filepath=item.path,
                    relative_path=True,

                    import_curves=True,
                    import_cameras=True,
                    import_lights=True,
                    import_materials=True,
                    import_meshes=True,
                    import_volumes=True,
                    import_shapes=True,
                    import_skeletons=True,
                    import_blendshapes=True,
                    import_points=True,
                    import_subdiv=False,
                    support_scene_instancing=True,
                    create_collection=True,
                    read_mesh_uvs=True,
                    read_mesh_colors=True,
                    read_mesh_attributes=True,
                    import_usd_preview=True,
                    set_material_blend=True,
                    light_intensity_scale=1,
                    mtl_name_collision_mode="MAKE_UNIQUE",
                    attr_import_mode="ALL",
                    create_world_material=True,
                )

                imported_collections = [
                    coll for coll in bpy.data.collections if coll.name.lower() in os.path.basename(item.path).lower()]
                
                if imported_collections:
                    # Use the most recent one in case there are duplicates
                    imported_collection = imported_collections[-1]
                    
                    # Rename it to our desired name
                    imported_collection.name = new_collection_name

                    if metadata:
                        version = metadata.get("version", 1)  # Default to version 1 if not specified
                        url = os.path.join(metadata.get("asset_url", ""), "stage.usd")

                        # Assign to collection
                        utils.set_primvar(imported_collection, "version", version)
                        utils.set_primvar(imported_collection, "url", url)

                        def assign_properties_to_objects(collection):
                            for obj in collection.objects:

                                if ("_GES" in obj.name or utils.check_primvar(obj.data, "subdivisionScheme")) and obj.type == "MESH":
                                    has_subdiv = any(mod.type == 'SUBSURF' for mod in obj.modifiers)
                                    if not has_subdiv:
                                        subdiv_level = utils.get_primvar(obj.data, "subdivisionLevels", 1) 

                                        # Add new subdivision modifier at end of stack
                                        subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
                                        subdiv.levels = max(1, int(subdiv_level/2))  # Set default subdivision level
                                        subdiv.render_levels = subdiv_level
                                        subdiv.subdivision_type = "SIMPLE" if utils.get_primvar(obj.data, "subdivisionScheme", "") == "loop" else "CATMULL_CLARK"
                                        subdiv.show_only_control_edges = True
                                        print(f"Added Subdivision modifier to: {obj.name}")

                                        # Ensure it's the last modifier in stack
                                        if obj.modifiers[-1] != subdiv:
                                            # Move to last position
                                            for i in range(len(obj.modifiers)):
                                                if obj.modifiers[i] == subdiv:
                                                    bpy.ops.object.modifier_move_to_index(
                                                        {"object": obj},
                                                        modifier=subdiv.name,
                                                        index=len(obj.modifiers)-1
                                                    )
                                                    break

                                elif ("_PLY" in obj.name) and obj.type == "MESH":
                                    obj.hide_render = True

                                # Also assign to object data (meshes, curves, etc.)
                                if obj.data:
                                    obj.data["version"] = version
                                    obj.data["url"] = url
                            
                            # Recursively process child collections
                            for child_collection in collection.children:
                                assign_properties_to_objects(child_collection)

                        assign_properties_to_objects(imported_collection)
                else:
                    print("Warning: USD import didn't create expected collection")

        except Exception as e:
            print(f"Error adding asset to scene: {str(e)}")
            return {"CANCELLED"}
        
        return {"FINISHED"}

class STUDIOTOOLS_IO_OT_RemoveImportItem(bpy.types.Operator):
    bl_idname = "studiotools_io.remove_import_item"
    bl_label = "Remove Import Item"
    
    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        return len(context.scene.studiotools_io.import_items) > 0

    def execute(self, context):

        scene = context.scene
        items = scene.studiotools_io.import_items
        
        # Remove the actual asset from the scene first
        self.remove_asset_from_scene(context, items[self.index])
        
        # Remove the item from the collection
        items.remove(self.index)
        
        # Update active index
        if scene.studiotools_io.active_item_index >= len(items):
            scene.studiotools_io.active_item_index = max(0, len(items) - 1)
        
        return {'FINISHED'}

            
    def remove_asset_from_scene(self, context, item):
        if item.type == 'TEX':
            target_path = bpy.path.abspath(item.path)

            for img in bpy.data.images:
                if bpy.data.abspath(img.filepath) == target_path:
                    users = img.users
                    if (users): img.user_clear()
                    bpy.data.images.remove(img)

        elif item.type == "LINK":
            lib_path = bpy.path.abspath(item.path)

            for coll in bpy.data.collections:
                if coll.library and bpy.path.abspath(coll.library.filepath) == lib_path:
                    self._unlink_collection(coll)
            
            for lib in bpy.data.libraries:
                if bpy.path.abspath(lib.filepath) == lib_path:
                    bpy.data.libraries.remove(lib)

        elif item.type == 'USD':            
            for coll in bpy.data.collections:
                if (utils.validate_primvar(coll, "url", item.path)):
                    bpy.data.collections.remove(coll)
            
            for obj in bpy.data.objects:
                if (utils.validate_primvar(obj, "url", item.path)):
                    bpy.data.objects.remove(obj, do_unlink=True)

    def _unlink_collection(self, collection):
        """Recursively unlink a collection and its children"""
        # Unlink child collections first
        for child in collection.children:
            self._unlink_collection(child)
        
        # Unlink all objects in this collection
        for obj in collection.objects:
            if obj.users == 1:  # Only used by this collection
                bpy.data.objects.remove(obj)
        
        # Remove collection from all scenes
        for scene in bpy.data.scenes:
            if collection.name in scene.collection.children:
                scene.collection.children.unlink(collection)
        
        # Remove collection if no users left
        if collection.users == 0:
            bpy.data.collections.remove(collection)

classes = [STUDIOTOOLS_IO_OT_Export, STUDIOTOOLS_IO_OT_AddImportItem, STUDIOTOOLS_IO_OT_RemoveImportItem]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)