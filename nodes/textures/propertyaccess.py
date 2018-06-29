import bpy
from bpy.types import PropertyGroup, NodeReroute, bpy_struct as Struct
from bpy.props import StringProperty, PointerProperty, EnumProperty, BoolProperty, IntProperty
from .. import LuxCoreNodeTexture
from ...utils import ui as utils_ui
from ...utils import node as utils_node
from . objectselect import LuxCoreNodeTexSelectObject, LuxCoreObjectPointers

# Overview
#
# Possible outputs:
#   * Color
#   * Vector
#   * Value (float)
#   * Object
#
# Input:
#   * Object
#
# Parent nodes will always be objects/keyed types
#
# If the currently selected property is iterable,
# slice and index options will be presented.

BLACKLISTED_PROPERTIES = ["owner", "is_frozen", "order", "is_wrapped"]

SUPPORTS_CUSTOM_PROPS = [bpy.types.ID, bpy.types.Bone, bpy.types.PoseBone]


def proper_case_property(p):
    """
    Change snake case to proper case except single-letter words
    """
    return ' '.join(
        [x.capitalize() if len(x) > 1 else x for x in p.split('_')]
    )


class LuxCoreNodeTexPropertyAccess(LuxCoreNodeTexture):
    bl_label = "Property Access"

    def get_interpretations(self, context):
        INDEXED = ("indexed", "Indexed", "")
        COLOR = ("color", "Color", "")
        VECTOR_2D = ("vector2d", "Vector 2D", "")
        VECTOR_3D = ("vector3d", "Vector 3D", "")

        interpretations = [INDEXED]

        if self.list_elements >= 3:
            interpretations.extend([COLOR, VECTOR_3D])

        if self.list_elements >= 2:
            interpretations.append(VECTOR_2D)

        return interpretations

    def on_select_interpretation(self, context):
        pass

    interpret_list_as = EnumProperty(
        name="Interpret List As",
        items=get_interpretations,
        update=on_select_interpretation
    )

    parent_name = StringProperty(name="Parent Name")
    property_name = StringProperty(name="PropertyName")

    selected_property = StringProperty(name="Selected Property")

    def get_properties(self, context):
        PASSTHROUGH = [("Passthrough", "Passthrough", "")]

        # Cannot set properties from here, so resolve in read_only mode
        (_, parent_object, _) = self.resolve(read_only=True)

        # Check if the key is a valid property
        def valid_key(key):
            if key.startswith("__") or key in BLACKLISTED_PROPERTIES:
                return False
            else:
                child_object = getattr(parent_object, key)

                if child_object is None:
                    return False
                elif callable(child_object) and not isinstance(child_object, Struct):
                    # Callable functions that would not otherwise have subproperties
                    # should be avoided
                    return False
                elif isinstance(child_object, str):
                    # Strings are kind of pointless here
                    return False

            return True

        if parent_object is not None:
            if any([isinstance(parent_object, ty) for ty in SUPPORTS_CUSTOM_PROPS]):
                keys = parent_object.keys()
            else:
                keys = filter(valid_key, dir(parent_object))

            return list(map(lambda p: (p, proper_case_property(p), ""), keys)) + PASSTHROUGH
        else:
            return PASSTHROUGH

    def on_select_property(self, context):
        self.selected_property = self.properties

        self.property_name = proper_case_property(self.selected_property)

        if "color" in self.selected_property:
            self.interpret_list_as = "color"

    properties = EnumProperty(
        name="Properties",
        items=get_properties,
        update=on_select_property)

    # True is the currently selected property is a list
    selected_is_list = BoolProperty(name="Is List")

    # True is there is a valid parent tree
    valid_parent = BoolProperty(name="Valid Parent")

    # True is the current selected property is valid
    valid_selection = BoolProperty(name="Valid Selection")

    list_elements = IntProperty(name="List Elements")

    real_list_index = IntProperty(name="Real List Index")

    def get_list_index(self):
        return self.real_list_index

    def set_list_index(self, value):
        self.real_list_index = max(0, min(value, self.list_elements - 1))

    list_index = IntProperty(
        name="First Index",
        min=0,
        get=get_list_index,
        set=set_list_index
    )

    def init(self, context):
        self.outputs.new("LuxCoreSocketProperty",
                         "Object", identifier="Object")
        self.outputs.new("LuxCoreSocketColor", "Color")
        self.outputs.new("LuxCoreSocketFloatUnbounded", "Value")

        self.outputs["Color"].enabled = False
        self.outputs["Value"].enabled = False

        self.add_input("LuxCoreSocketProperty", "Object")

    def update_sockets(self):
        pass
        # if not self.valid_parent or not self.valid_selection:
        #     for output in self.outputs:
        #         output.enabled = False
        # else:
        #     pass

    def resolve(self, read_only=False):
        """
        Recursively resolves properties from chained objects and selectors

        Returns (valid parent tree, parent object, selected child object)
        """
        INVALID = (False, None, None)

        input = self.inputs.get("Object")

        if input is None:
            return INVALID

        links = input.links

        if len(links) == 1:
            parent_node = links[0].from_node

            # resolve reroutes
            while isinstance(parent_node, NodeReroute):
                reroute_input = parent_node.inputs.get("Input")

                if reroute_input is None:
                    return INVALID
                else:
                    reroute_links = reroute_input.links

                    if len(reroute_links) > 0:
                        parent_node = reroute_links[0].from_node

            valid_parent = False
            parent_object = None

            if isinstance(parent_node, LuxCoreNodeTexSelectObject):
                valid_parent = True

                parent_object = getattr(
                    parent_node.pointers,
                    parent_node.datablock_type
                )

                if not read_only:
                    self.parent_name = parent_object.name

            elif isinstance(parent_node, LuxCoreNodeTexPropertyAccess):
                (valid_parent, _, parent_object) = parent_node.resolve(read_only)

                if not read_only:
                    self.parent_name = parent_node.property_name

            if valid_parent:
                child_object = None
                iterable = False

                if parent_object is not None and self.selected_property:
                    if self.selected_property == "Passthrough":
                        child_object = parent_object
                    elif hasattr(parent_object, self.selected_property):
                        child_object = getattr(
                            parent_object, self.selected_property)

                    iterable = \
                        isinstance(child_object, slice) or  \
                        isinstance(child_object, list) or   \
                        hasattr(child_object, "__getitem__")

                    if not iterable and not isinstance(child_object, Struct):
                        try:
                            iter(child_object)
                            iterable = True
                        except TypeError:
                            pass

                    if iterable:
                        if not read_only:
                            self.list_elements = len(child_object)

                        try:
                            child_object = child_object[self.list_index]
                        except:
                            # Invalid slice/index, so there is no child
                            child_object = None

                    if not read_only:
                        self.selected_is_list = iterable

                        self.valid_selection = child_object is not None

                    return (valid_parent, parent_object, child_object)

        return INVALID

    def socket_value_update(self, context):
        (self.valid_parent, _, _) = self.resolve()

    def update(self):
        (self.valid_parent, _, _) = self.resolve()

    def draw_label(self):
        if self.valid_parent:
            return "Accessing {} from {}".format(self.property_name, self.parent_name)
        else:
            return self.bl_label

    def draw_buttons(self, context, layout):
        if self.valid_parent:
            layout.prop(self, "properties", text="Property")

            if self.valid_selection:
                if self.selected_is_list:
                    layout.prop(self, "interpret_list_as", text="Interpret")

                    if self.interpret_list_as == "indexed":
                        layout.prop(self, "list_index", text="Index")
            else:
                layout.label("Invalid Selection!", icon="CANCEL")
        else:
            layout.label("Invalid Input!", icon="CANCEL")
