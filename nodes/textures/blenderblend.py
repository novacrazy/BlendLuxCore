import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty
from .. import LuxCoreNodeTexture

from .. import sockets
from ... import utils

class LuxCoreNodeTexBlenderBlend(LuxCoreNodeTexture):
    bl_label = "Blender Blend"
    bl_width_default = 200    

    progression_items = [
        ("linear", "Linear", "linear"),
        ("quadratic", "Quadratic", "quadratic"),
        ("easing", "Easing", "easing"),
        ("diagonal", "Diagonal", "diagonal"),
        ("spherical", "Spherical", "spherical"),
        ("halo", "Quadratic Sphere", "quadratic sphere"),
        ("radial", "Radial", "radial"),
    ]

    direction_items = [
        ("horizontal", "Horizontal", "Direction: -x to x"),
        ("vertical", "Vertical", "Direction: -y to y")
    ]

    progression_type = EnumProperty(name="Progression", description="progression", items=progression_items, default="linear")
    direction = EnumProperty(name="Direction", items=direction_items)

    bright = FloatProperty(name="Brightness", default=1.0, min=0)
    contrast = FloatProperty(name="Contrast", default=1.0, min=0)

    def init(self, context):
        self.add_input("LuxCoreSocketMapping3D", "3D Mapping")
        self.outputs.new("LuxCoreSocketColor", "Color")

    def draw_buttons(self, context, layout):
        layout.prop(self, "direction", expand=True)
        layout.prop(self, "progression_type")
        layout.separator()
        column = layout.column(align=True)
        column.prop(self, "bright")
        column.prop(self, "contrast")

    def export(self, props, luxcore_name=None):
        mapping_type, transformation = self.inputs["3D Mapping"].export(props)
       
        definitions = {
            "type": "blender_blend",
            "progressiontype": self.progression_type,
            "direction": self.direction,
            "bright": self.bright,
            "contrast": self.contrast,
            # Mapping
            "mapping.type": mapping_type,
            "mapping.transformation": utils.matrix_to_list(transformation),
        }
        
        return self.base_export(props, definitions, luxcore_name)
