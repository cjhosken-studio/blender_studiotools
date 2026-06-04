try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

from utils import update_default_asset_name, update_default_render_name

if IN_BLENDER:
    @bpy.app.handlers.persistent
    def update_default_asset_name_handler(dummy1=None, dummy2=None):
        update_default_asset_name()
        update_default_render_name()

    @bpy.app.handlers.persistent
    def sync_materials_viewport_color(scene, depsgraph):
        """
        Callback that runs on every scene depsgraph update.
        Synchronizes Principled BSDF base color with the material's Viewport Display color.
        """
        try:
            for mat in bpy.data.materials:
                if not mat.use_nodes or not mat.node_tree:
                    continue
                
                # Find Principled BSDF node
                principled = None
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled = node
                        break
                        
                if principled:
                    base_color_input = principled.inputs.get('Base Color') or (principled.inputs[0] if principled.inputs else None)
                    if base_color_input and not base_color_input.is_linked:
                        val = base_color_input.default_value
                        diff = sum(abs(a - b) for a, b in zip(mat.diffuse_color, val))
                        if diff > 1e-4:
                            mat.diffuse_color = val
        except Exception:
            pass
else:
    # Fallbacks for non-Blender environment compilation
    def update_default_asset_name_handler(dummy1=None, dummy2=None):
        pass
    def sync_materials_viewport_color(scene, depsgraph):
        pass
