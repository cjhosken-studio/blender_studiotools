import bpy

class STUDIOTOOLS_IO_ImportItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name",
        description="Name of the asset"
    )

    path: bpy.props.StringProperty(
        name="Path",
        description="Path to the asset to import",
        subtype='FILE_PATH'
    )

    type: bpy.props.EnumProperty(
        name="Type",
        description="Type of asset (texture, usd, link)",
        items = [
            ("NONE", "None", "None"),
            ("USD", ".usd", "USD File"),
            ("LINK", "Blender Library", "Blender Library"),
            ("TEX", "Texture", "Texture"),
            ("CACHE", "Cache", "Cache")
        ],
        default="NONE"
    )

class STUDIOTOOLS_IO_Properties(bpy.types.PropertyGroup):

    export_usd: bpy.props.BoolProperty(
        name="Export USD",
        description="Export as USD format",
        default=True
    )

    export_usd_type: bpy.props.EnumProperty(
        name="USD Type",
        description="",
        items = [
            ("USD", ".usd", ""),
            ("USDA", ".usda", ""),
            ("USDC", ".usdc", ""),
            ("USDZ", ".usdz", "")
        ],
        default="USD"
    )

    export_usd_meshes: bpy.props.BoolProperty(
        name="Export Meshes",
        description="Export USD meshes",
        default=True
    )

    export_usd_lights: bpy.props.BoolProperty(
        name="Export Lights",
        description="Export USD lights",
        default=False
    )

    export_usd_cameras: bpy.props.BoolProperty(
        name="Export Cameras",
        description="Export USD cameras",
        default=False
    )

    export_usd_curves: bpy.props.BoolProperty(
        name="Export Curves/Hair",
        description="Export USD curves and hair",
        default=True
    )

    export_usd_points: bpy.props.BoolProperty(
        name="Export Points",
        description="Export USD point",
        default=True
    )

    export_usd_volumes: bpy.props.BoolProperty(
        name="Export Volumes",
        description="Export USD volumes",
        default=False
    )

    export_usd_animation: bpy.props.BoolProperty(
        name="Export Animation",
        description="Export a USD animation",
        default=False
    )

    export_usd_materials: bpy.props.BoolProperty(
        name="Export Materials",
        description="Export materials for USD",
        default=False
    )

    export_usd_materials_mtlx: bpy.props.BoolProperty(
        name="Export Materialx",
        description="Export materialx materials for USD",
        default=False
    )

    export_usd_materials_usd: bpy.props.BoolProperty(
        name="Export USD Preview",
        description="Export usd preview materials for USD",
        default=False
    )

    export_usd_textures_mode: bpy.props.EnumProperty(
        name="External Texture Mode",
        description="Decide how to deal with external textures",
        items = [
            ("KEEP", "Keep", "Use original location of the textures"),
            ("PRESERVE", "Preserve", "Preserve file paths of textures from already imported USD files. Export the rest into a 'textures' folder"),
            ("NEW", "New Path", "Export textures to a 'textures' folder next to the usd file.")
        ],
        default="KEEP"
    )

    export_usd_textures_usdz_mode: bpy.props.EnumProperty(
        name="USDZ Texture Downsampling",
        description="Downsample textures for USDZ files",
        items = [
            ("KEEP", "Keep", "Keep"),
            ("256", "256", ""),
            ("512", "512", ""),
            ("1024", "1024", ""),
            ("2048", "2048", ""),
            ("4096", "4096", ""),
            ("CUSTOm", "Custom", "")
        ],
        default="KEEP"
    )

    export_usd_textures_usdz_size: bpy.props.IntProperty(
        name="USDZ Texture Downsampling size",
        description="",
        default = 128
    )

    export_usd_rigs: bpy.props.BoolProperty(
        name="Export Rigging",
        description="Export Armatures & Blendshapes",
        default=False
    )
    
    export_usd_relative: bpy.props.BoolProperty(
        name="Use relative texture paths",
        default=True
    )

    export_blend: bpy.props.BoolProperty(
        name="Export Blend",
        description="Export as Blend format",
        default=False
    )

    export_version: bpy.props.IntProperty(
        name="Export Version",
        default=1
    )

    export_path: bpy.props.StringProperty(
        name="Export Path",
        description="Export path",
        default="./asset"
    )

    import_items: bpy.props.CollectionProperty(type=STUDIOTOOLS_IO_ImportItem)
    active_item_index: bpy.props.IntProperty()


classes = [STUDIOTOOLS_IO_ImportItem, STUDIOTOOLS_IO_Properties]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.studiotools_io = bpy.props.PointerProperty(type=STUDIOTOOLS_IO_Properties)

def unregister():
    del bpy.types.Scene.studiotools_io

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)