import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, PointerProperty, EnumProperty
from .. import LuxCoreNodeTexture
from ...utils import ui as utils_ui
from ...utils import node as utils_node

datablock_icons = {
    'Mesh': "MESH_DATA",
    'Screen': "SPLITSCREEN",
    'NodeTree': "NODETREE",
    'ParticleSettings': "PARTICLE_DATA",
    # 'WindowManager': "NONE",
    'World': "WORLD",
    'Lattice': "LATTICE_DATA",
    'Object': "OBJECT_DATA",
    'Brush': "BRUSH_DATA",
    'Lamp': "LAMP_DATA",
    'Armature': "ARMATURE_DATA",
    'Image': "IMAGE_DATA",
    'Camera': "CAMERA_DATA",
    'Curve': "CURVE_DATA",
    'MetaBall': "META_DATA",
    'Material': "MATERIAL_DATA",
    'FreestyleLineStyle': "LINE_DATA",
    'Scene': "SCENE_DATA",
    'Speaker': "SPEAKER",
    'Text': "TEXT",
    'Texture': "TEXTURE_DATA",
}


class LuxCoreObjectPointers(PropertyGroup):
    pass


# Sort these first specifically
FORCED_ORDER = [bpy.types.Object,
                bpy.types.Mesh,
                bpy.types.Lamp,
                bpy.types.Material,
                bpy.types.Camera,
                bpy.types.World]


def get_ID_subclasses():
    raw = [cls for cls in bpy.types.ID.__subclasses__()
           if cls not in {bpy.types.Library,
                          bpy.types.Group,
                          bpy.types.Sound,
                          bpy.types.WindowManager}]

    def key(x):
        try:
            return FORCED_ORDER.index(x)
        except ValueError:
            # Offset real index by length of ordered list to avoid collisions
            return raw.index(x) + len(FORCED_ORDER)

    return sorted(raw, key=key)


for cls in get_ID_subclasses():
    setattr(LuxCoreObjectPointers, cls.__name__, PointerProperty(type=cls))


class LuxCoreNodeTexSelectObject(LuxCoreNodeTexture):
    bl_label = "Select Object"

    def update_sockets(self, context):
        self.outputs[0].name = self.datablock_type

    pointers = PointerProperty(type=LuxCoreObjectPointers)
    datablock_types = [(cls.__name__, cls.__name__, "", datablock_icons[cls.__name__], i)
                       for i, cls in enumerate(get_ID_subclasses())]
    datablock_type = EnumProperty(name="Data Type", items=datablock_types, default="Object",
                                  update=update_sockets)

    def init(self, context):
        self.outputs.new("LuxCoreSocketProperty",
                         "Object", identifier="Object")

    def draw_label(self):
        return "Select " + self.datablock_type

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Data Type")
        layout.prop(self.pointers, self.datablock_type)
