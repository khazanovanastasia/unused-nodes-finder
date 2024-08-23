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
    
    def clear_previous_results(self):
        def clear_tree(node_tree):
            nodes_to_remove = []
            links_to_remove = []
            
            for node in node_tree.nodes:
                if node.type == 'ATTRIBUTE':
                    nodes_to_remove.append(node)
                    print(f"Marking Attribute node for removal: {node.name}")
                elif node.type == 'FRAME' and node.label == "Unused Nodes":
                    for child in node_tree.nodes:
                        if child.parent == node:
                            child.parent = None
                            print(f"Unparenting node: {child.name}")
                    nodes_to_remove.append(node)
                    print(f"Marking Frame node for removal: {node.name}")
                elif node.type == 'NODE_GROUP' and node.node_tree:
                    clear_tree(node.node_tree)
            
            for link in node_tree.links:
                if link.from_node in nodes_to_remove or link.to_node in nodes_to_remove:
                    links_to_remove.append(link)
                    print(f"Marking link for removal: {link.from_node.name} -> {link.to_node.name}")
            
            for link in links_to_remove:
                node_tree.links.remove(link)
                print(f"Removed link")
            
            for node in nodes_to_remove:
                node_tree.nodes.remove(node)
                print(f"Removed node")

        for material in bpy.data.materials:
            if material.use_nodes:
                clear_tree(material.node_tree)

        self.report({'INFO'}, "Cleared previous results")
        print("Finished clearing previous results")
                            
    def find_unused_nodes(self):
        unused_nodes = []
        for material in bpy.data.materials:
            if material.use_nodes:
                unused_nodes.extend(self.find_unused_nodes_recursive(material.node_tree, material.name))
        return unused_nodes

    def find_unused_nodes_recursive(self, node_tree, material_name, parent_node=None):
        unused_nodes = []
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
                if node not in linked_nodes and node.type not in ['FRAME', 'ATTRIBUTE']:
                    if parent_node:
                        unused_nodes.append((material_name, parent_node, node))
                    else:
                        unused_nodes.append((material_name, node))
                
                # Рекурсивно проверяем группы нод
                if node.type == 'NODE_GROUP' and node.node_tree:
                    group_unused_nodes = self.find_unused_nodes_recursive(node.node_tree, material_name, node)
                    unused_nodes.extend(group_unused_nodes)
        
        return unused_nodes

    def print_unused_nodes(self, unused_nodes):
        if not unused_nodes:
            self.report({'INFO'}, "No unused nodes found.")
        else:
            self.report({'INFO'}, "Found the following unused nodes:")
            for item in unused_nodes:
                if len(item) == 2:
                    material_name, node = item
                    self.report({'INFO'}, f"Material: {material_name}, Node: {node.name}, Type: {node.type}")
                    if node.type == 'NODE_GROUP':
                        self.report({'INFO'}, "  This node is a group. Used in materials:")
                        for mat in bpy.data.materials:
                            if mat.use_nodes:
                                for n in mat.node_tree.nodes:
                                    if n.type == 'NODE_GROUP' and n.node_tree == node.node_tree:
                                        self.report({'INFO'}, f"  - {mat.name}")
                else:
                    material_name, parent_node, node = item
                    self.report({'INFO'}, f"Material: {material_name}, Group: {parent_node.name}, Node: {node.name}, Type: {node.type}")
        
    def add_attribute_node(self, material, unused_node, parent_node=None):
        node_tree = parent_node.node_tree if parent_node else material.node_tree
        
        for node in node_tree.nodes:
            if node.type == 'ATTRIBUTE' and node.location == (unused_node.location.x - 200, unused_node.location.y):
                return
        
        attribute_node = node_tree.nodes.new(type='ShaderNodeAttribute')
        attribute_node.location = (unused_node.location.x - 200, unused_node.location.y)
        
        if unused_node.inputs:
            for input in unused_node.inputs:
                if input.enabled and not input.is_linked:
                    node_tree.links.new(attribute_node.outputs[0], input)
                    break
        else:
            print(f"Node {unused_node.name} has no inputs, Attribute node added but not connected")
        
        # If the unused node is inside a NodeGroup, we need to add the Attribute node to the frame as well
        if parent_node and parent_node.type == 'NODE_GROUP':
            frame = next((n for n in node_tree.nodes if n.type == 'FRAME' and n.label == "Unused Nodes"), None)
            if frame:
                attribute_node.parent = frame

    def organize_unused_nodes(self, material, unused_nodes):
        def organize_in_tree(node_tree, nodes_to_organize, parent_frame=None):
            frame = parent_frame or next((n for n in node_tree.nodes if n.type == 'FRAME' and n.label == "Unused Nodes"), None)
            if not frame:
                frame = node_tree.nodes.new(type='NodeFrame')
                frame.label = "Unused Nodes"
                frame.use_custom_color = True
                frame.color = (1, 0.5, 0.5)
                
                used_nodes = [n for n in node_tree.nodes if n not in nodes_to_organize]
                if used_nodes:
                    max_x = max(node.location.x for node in used_nodes)
                    frame.location = (max_x + 300, 0)
            
            for node in nodes_to_organize:
                if node.id_data is not None:
                    node.parent = frame
                    node.location.x = frame.location.x + node.location.x - frame.location.x
                    node.location.y = frame.location.y + node.location.y - frame.location.y
                    
                    if node.type == 'NODE_GROUP' and node.node_tree:
                        group_unused_nodes = [n for n in node.node_tree.nodes if any(un[2] == n for un in unused_nodes if len(un) == 3 and un[1] == node)]
                        organize_in_tree(node.node_tree, group_unused_nodes)
                    
                    for other_node in node_tree.nodes:
                        if other_node.type == 'ATTRIBUTE' and other_node.location == (node.location.x - 200, node.location.y):
                            other_node.parent = frame
                            other_node.location.x = frame.location.x + other_node.location.x - frame.location.x
                            other_node.location.y = frame.location.y + other_node.location.y - frame.location.y

        material_nodes = [node for _, *rest in unused_nodes if _ == material.name for node in (rest if len(rest) == 1 else rest[1:])]
        organize_in_tree(material.node_tree, material_nodes)
        
        print(f"Organized unused nodes in material: {material.name}")
        
    def execute(self, context):
        self.clear_previous_results()
        unused_nodes = self.find_unused_nodes()
        self.print_unused_nodes(unused_nodes)

        for item in unused_nodes:
            if len(item) == 2:
                material_name, node = item
                material = bpy.data.materials[material_name]
                self.add_attribute_node(material, node)
            else:
                material_name, parent_node, node = item
                material = bpy.data.materials[material_name]
                self.add_attribute_node(material, node, parent_node)

        for material in bpy.data.materials:
            material_unused_nodes = [item for item in unused_nodes if item[0] == material.name]
            if material_unused_nodes:
                self.organize_unused_nodes(material, material_unused_nodes)

        return {'FINISHED'}

        
class UNUSED_NODES_PT_main_panel(Panel):
    bl_label = "Unused Nodes Finder"
    bl_idname = "UNUSED_NODES_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        layout.operator("unused_nodes.find_and_organize", text="Find and Organize Unused Nodes")

print("Panel class defined")


def register():
    bpy.utils.register_class(UNUSED_NODES_OT_find_and_organize)
    bpy.utils.register_class(UNUSED_NODES_PT_main_panel)


def unregister():
    bpy.utils.unregister_class(UNUSED_NODES_OT_find_and_organize)
    bpy.utils.unregister_class(UNUSED_NODES_PT_main_panel)


if __name__ == "__main__":
    register()