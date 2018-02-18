from bpy.props import FloatProperty, BoolProperty, EnumProperty
from .. import LuxCoreNodeMaterial, Roughness
from .. import utils

class LuxCoreNodeMatMetal(LuxCoreNodeMaterial):
    """metal material node"""
    bl_label = "Metal Material"
    bl_width_default = 200

    # For internal use, do not show in UI
    is_first_input_change = BoolProperty(default=True)

    def change_input_type(self, context):
        is_fresnel = self.input_type == "fresnel"
        is_color = self.input_type == "color"

        self.inputs["Fresnel"].enabled = is_fresnel
        self.inputs["Color"].enabled = is_color

        # The first time the user switches to "fresnel" mode,
        # add a fresnel texture automatically
        if is_fresnel and self.is_first_input_change:
            self.is_first_input_change = False
            node_tree = self.id_data
            fresnel_tex = node_tree.nodes.new("LuxCoreNodeTexFresnel")
            fresnel_tex.location = (self.location.x - 300, self.location.y)
            node_tree.links.new(fresnel_tex.outputs[0], self.inputs["Fresnel"])

    input_type_items = [
        ("color", "Color", "Use custom color as input", 0),
        ("fresnel", "Fresnel Texture", "Use a fresnel texture as input", 1)
    ]
    input_type = EnumProperty(name="Type", description="Input Type", items=input_type_items, default="color",
                                        update=change_input_type)

    use_anisotropy = BoolProperty(name=Roughness.aniso_name,
                                  default=False,
                                  description=Roughness.aniso_desc,
                                  update=Roughness.update_anisotropy)

    def init(self, context):
        self.add_input("LuxCoreSocketColor", "Color", (0.7, 0.7, 0.7))
        self.inputs.new("LuxCoreSocketFresnel", "Fresnel")
        self.inputs["Fresnel"].enabled = False        
        Roughness.init(self, 0.05)
        
        self.add_common_inputs()

        self.outputs.new("LuxCoreSocketMaterial", "Material")

    def draw_buttons(self, context, layout):
        layout.prop(self, "input_type", expand=True)
        Roughness.draw(self, context, layout)

    def export(self, props, luxcore_name=None):
        definitions = {
            "type": "metal2",
        }

        if self.input_type == "fresnel":
            definitions["fresnel"] = self.inputs["Fresnel"].export(props)
        else:            
            # Implicitly create a fresnelcolor texture with unique name
            tex_name = self.make_name() + "fresnel_helper"
            helper_prefix = "scene.textures." + tex_name + "."
            helper_defs = {
                "type": "fresnelcolor",
                "kr": self.inputs["Color"].export(props),
            }
            props.Set(utils.create_props(helper_prefix, helper_defs))

            definitions["fresnel"] = tex_name
            
        Roughness.export(self, props, definitions)
        self.export_common_inputs(props, definitions)
        return self.base_export(props, definitions, luxcore_name)
