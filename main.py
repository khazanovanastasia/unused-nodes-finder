print("Starting to load the addon")

import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty, BoolProperty

print("Imports successful")

class UNUSED_NODES_OT_find_and_organize(Operator):
    bl_idname = "unused_nodes.find_and_organize"
    bl_label = "Find and Organize Unused Nodes"
    bl_description = "Find unused nodes in materials and organize them"
    bl_options = {'REGISTER', 'UNDO'}
        
    def find_unused_nodes(self):
        unused_nodes = []

        for material in bpy.data.materials:
            if material.use_nodes:
                node_tree = material.node_tree
                output_node = node_tree.get_output_node('ALL')

                if output_node:
                    linked_nodes = set()
                    to_check = [output_node]

                    while to_check:
                        node = to_check.pop(0)
                        if node not in linked_nodes:
                            linked_nodes.add(node)
                            for input in node.inputs:
                                for link in input.links:
                                    to_check.append(link.from_node)

                    for node in node_tree.nodes:
                        if node not in linked_nodes and node.type != 'FRAME':
                            unused_nodes.append((material.name, node))

        return unused_nodes

    def print_unused_nodes(self, unused_nodes):
        if not unused_nodes:
            self.report({'INFO'}, "No unused nodes found.")
        else:
            self.report({'INFO'}, "Found the following unused nodes:")
            for material_name, node in unused_nodes:
                self.report({'INFO'}, f"Material: {material_name}, Node: {node.name}, Type: {node.type}")
                if node.type == 'GROUP':
                    self.report({'INFO'}, "  This node is a group. Used in materials:")
                    for mat in bpy.data.materials:
                        if mat.use_nodes:
                            for n in mat.node_tree.nodes:
                                if n.type == 'GROUP' and n.node_tree == node.node_tree:
                                    self.report({'INFO'}, f"  - {mat.name}")

    def add_attribute_node(self, material, unused_node):
        node_tree = material.node_tree
        attribute_node = node_tree.nodes.new(type='ShaderNodeAttribute')
        attribute_node.location = (unused_node.location.x - 200, unused_node.location.y)

        # Try to connect to the first available input
        for input in unused_node.inputs:
            if input.enabled and not input.is_linked:
                node_tree.links.new(attribute_node.outputs[0], input)
                break

    def organize_unused_nodes(self, material, unused_nodes):
        node_tree = material.node_tree
        frame = node_tree.nodes.new(type='NodeFrame')
        frame.label = "Unused Nodes"
        frame.use_custom_color = True
        frame.color = (1, 0.5, 0.5)  # Light red color

        # Position the frame
        used_nodes = [n for n in node_tree.nodes if n not in [node for _, node in unused_nodes]]
        if used_nodes:
            max_x = max(node.location.x for node in used_nodes)
            frame.location = (max_x + 300, 0)

        for _, node in unused_nodes:
            node.parent = frame
            node.location.x = frame.location.x + node.location.x - frame.location.x
            node.location.y = frame.location.y + node.location.y - frame.location.y

    def execute(self, context):
        unused_nodes = self.find_unused_nodes()
        self.print_unused_nodes(unused_nodes)

        for material_name, node in unused_nodes:
            material = bpy.data.materials[material_name]
            self.add_attribute_node(material, node)

        # Organize unused nodes by material
        for material in bpy.data.materials:
            material_unused_nodes = [(m, n) for m, n in unused_nodes if m == material.name]
            if material_unused_nodes:
                self.organize_unused_nodes(material, material_unused_nodes)

        return {'FINISHED'}
  
def menu_func(self, context):
    self.layout.operator(UNUSED_NODES_OT_find_and_organize.bl_idname)
      
print("Operator class defined")
    
class UNUSED_NODES_PT_main_panel(Panel):
    bl_label = "Unused Nodes Finder"
    bl_idname = "UNUSED_NODES_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Unused Nodes'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Debug: Panel is drawing")
        layout.operator("unused_nodes.find_and_organize", text="Find and Organize Unused Nodes")

print("Panel class defined")


def register():
    bpy.utils.register_class(UNUSED_NODES_OT_find_and_organize)
    bpy.utils.register_class(UNUSED_NODES_PT_main_panel)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(UNUSED_NODES_OT_find_and_organize)
    bpy.utils.unregister_class(UNUSED_NODES_PT_main_panel)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
    
