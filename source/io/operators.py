import os
import re
import bpy
from . import utils
from bpy_extras.io_utils import ImportHelper

class STUDIOTOOLS_IO_OT_Export(bpy.types.Operator):
    """Test"""
    bl_idname = "studiotools_io.export"
    bl_label = "Export"

    def execute(self, context):
        scene = context.scene

        studiotools = scene.studiotools
        studiotools_io = scene.studiotools_io

        # Process the filepath
        filepath = f"{studiotools_io.export_path}_v{studiotools_io.export_version:03d}"

        if (studiotools_io.export_usd):
            usd_filepath = os.path.join(filepath, f"stage.{studiotools_io.export_usd_type.lower()}")

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
                export_subdivision="IGNORE",

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

                export_custom_properties=True,
                custom_properties_namespace="primvars",
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


        if (studiotools_io.export_blend):
            blend_filepath = os.path.join(filepath, "scene.blend")

            # Get all objects (including nested collections)
            all_objects = utils.get_all_objects_from_collection(studiotools.selected_collection)

            # Gather all data blocks (objects, meshes, materials, etc.)
            data_blocks = set()
            # 1. Add the main collection and its children (if needed)
            data_blocks.add(studiotools.selected_collection)
            
            # Optional: Add all child collections recursively
            def add_collections_recursive(collection):
                for child in collection.children:
                    data_blocks.add(child)
                    add_collections_recursive(child)
            
            add_collections_recursive(studiotools.selected_collection)

            for obj in all_objects:
                data_blocks.add(obj)
                if obj.data:
                    data_blocks.add(obj.data)
                if hasattr(obj.data, 'materials'):
                    for mat in obj.data.materials:
                        if mat:
                            data_blocks.add(mat)

            bpy.data.libraries.write(
                filepath=blend_filepath, 
                datablocks=data_blocks, 
                fake_user=True,
                compress=True    
            )

        self.report({"INFO"}, "Export Complete!")

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
                    import_subdiv=True,
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
            base_name = item.name  # Get filename without extension
            
            # Remove version suffix (_v001, _v002 etc.) from base name
            clean_base_name = re.sub(r'_v\d+$', '', base_name)
            
            # Find matching collections (case insensitive)
            collections_to_remove = []
            for coll in bpy.data.collections:
                if clean_base_name.lower() == coll.name.lower():
                    collections_to_remove.append(coll)
            
            # Remove found collections and their contents
            for coll in collections_to_remove:
                # Unlink from all scenes first
                for scene in bpy.data.scenes:
                    if coll.name in scene.collection.children:
                        scene.collection.children.unlink(coll)
                
                # Recursively remove objects
                for obj in list(coll.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)
                
                # Remove the collection
                bpy.data.collections.remove(coll)
            
            # Additional cleanup for USD-specific data
            for obj in bpy.data.objects:
                if obj.get('usd_filepath') and bpy.path.abspath(obj['usd_filepath']) == lib_path:
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