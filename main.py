import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty, BoolProperty

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
                elif node.type == 'FRAME' and node.label == "Unused Nodes":
                    for child in node_tree.nodes:
                        if child.parent == node:
                            child.parent = None
                    nodes_to_remove.append(node)
                elif node.type == 'NODE_GROUP' and node.node_tree:
                    clear_tree(node.node_tree)
            
            for link in node_tree.links:
                if link.from_node in nodes_to_remove or link.to_node in nodes_to_remove:
                    links_to_remove.append(link)
            
            for link in links_to_remove:
                node_tree.links.remove(link)
            
            for node in nodes_to_remove:
                node_tree.nodes.remove(node)

        for material in bpy.data.materials:
            if material.use_nodes:
                clear_tree(material.node_tree)

        self.report({'INFO'}, "Cleared previous results")
        print("Finished clearing previous results")
                            
    def find_unused_nodes(self):
        unused_nodes = []
        
        def check_node_tree(material, node_tree, parent_node=None, path=[]):
            output_node = next((node for node in node_tree.nodes if node.type == 'OUTPUT_MATERIAL'), None)
            if not output_node:
                return
            
            used_nodes = set()
            nodes_to_check = [(output_node, path)]
            
            while nodes_to_check:
                current_node, current_path = nodes_to_check.pop(0)
                if current_node not in used_nodes:
                    used_nodes.add(current_node)
                    for input_socket in current_node.inputs:
                        for link in input_socket.links:
                            if link.from_node.type == 'NODE_GROUP' and link.from_node.node_tree:
                                new_path = current_path + [link.from_node]
                                nodes_to_check.append((link.from_node, new_path))
                                check_node_tree(material, link.from_node.node_tree, link.from_node, new_path)
                            else:
                                nodes_to_check.append((link.from_node, current_path))
            
            for node in node_tree.nodes:
                if node not in used_nodes and node.type != 'FRAME':
                    unused_nodes.append((material.name, path + [node]))
                
                if node.type == 'NODE_GROUP' and node.node_tree:
                    check_node_tree(material, node.node_tree, node, path + [node])
        
        for material in bpy.data.materials:
            if material.use_nodes:
                check_node_tree(material, material.node_tree)
        
        return unused_nodes

                
    def print_unused_nodes(self, unused_nodes):
        if not unused_nodes:
            self.report({'INFO'}, "No unused nodes found.")
        else:
            self.report({'INFO'}, "Found the following unused nodes:")
            for material_name, node_path in unused_nodes:
                node = node_path[-1]
                path_str = " -> ".join([n.name for n in node_path[:-1]])
                if path_str:
                    self.report({'INFO'}, f"Material: {material_name}, Path: {path_str}, Node: {node.name}, Type: {node.type}")
                else:
                    self.report({'INFO'}, f"Material: {material_name}, Node: {node.name}, Type: {node.type}")
                
                if node.type == 'NODE_GROUP':
                    self.report({'INFO'}, "  This node is a group. Used in materials:")
                    for mat in bpy.data.materials:
                        if mat.use_nodes:
                            for n in mat.node_tree.nodes:
                                if n.type == 'NODE_GROUP' and n.node_tree == node.node_tree:
                                    self.report({'INFO'}, f"  - {mat.name}")
                                    
    def add_attribute_node(self, material, unused_node_path):
        node_tree = material.node_tree
        unused_node = unused_node_path[-1] 
        for node in unused_node_path[:-1]:
            if node.type == 'NODE_GROUP' and node.node_tree:
                node_tree = node.node_tree
        
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
        
        frame = next((n for n in node_tree.nodes if n.type == 'FRAME' and n.label == "Unused Nodes"), None)
        if frame and unused_node.parent == frame:
            attribute_node.parent = frame
            
    def organize_unused_nodes(self, material, unused_nodes):
        def get_node_by_path(node_tree, path):
            if isinstance(path, str):
                nodes = path.split(' > ')
            elif isinstance(path, list):
                nodes = path
            else:
                raise TypeError("path must be either a string or a list")

            current_tree = node_tree
            for node in nodes[:-1]:
                if isinstance(node, str):
                    node = current_tree.nodes.get(node)
                if node and node.type == 'NODE_GROUP':
                    current_tree = node.node_tree
                else:
                    return None
            
            last_node = nodes[-1]
            if isinstance(last_node, str):
                return current_tree.nodes.get(last_node)
            else:
                return last_node

        def organize_in_tree(node_tree, nodes_to_organize, parent_frame=None):
            frame = parent_frame or next((n for n in node_tree.nodes if n.type == 'FRAME' and n.label == "Unused Nodes"), None)
            
            unused_nodes = [get_node_by_path(node_tree, node_path) for node_path in nodes_to_organize]
            unused_nodes = [node for node in unused_nodes if node]  
            
            if not frame and unused_nodes:
                frame = node_tree.nodes.new(type='NodeFrame')
                frame.label = "Unused Nodes"
                frame.use_custom_color = True
                frame.color = (1, 0.5, 0.5)
                
                avg_x = sum(node.location.x for node in unused_nodes) / len(unused_nodes)
                avg_y = sum(node.location.y for node in unused_nodes) / len(unused_nodes)
            
                frame.location = (avg_x, avg_y)
            
            for node_path in nodes_to_organize:
                node = get_node_by_path(node_tree, node_path)
                if node:
                    node.parent = frame
                    #node.location.x = frame.location.x + node.location.x - frame.location.x
                    #node.location.y = frame.location.y + node.location.y - frame.location.y
                    
                    if node.type == 'NODE_GROUP' and node.node_tree:
                        group_unused_nodes = [item[1] for item in unused_nodes if item[0] == material.name and isinstance(item[1], list) and item[1][0] == node]
                        organize_in_tree(node.node_tree, group_unused_nodes)
                    
                    for other_node in node_tree.nodes:
                        if other_node.type == 'ATTRIBUTE' and other_node.location == (node.location.x - 200, node.location.y):
                            other_node.parent = frame
                            other_node.location.x = frame.location.x + other_node.location.x - frame.location.x
                            other_node.location.y = frame.location.y + other_node.location.y - frame.location.y

        material_nodes = [item[1] if len(item) == 2 else item[1:] for item in unused_nodes if item[0] == material.name]
        organize_in_tree(material.node_tree, material_nodes)

    def execute(self, context):
        self.clear_previous_results()
        unused_nodes = self.find_unused_nodes()
        self.print_unused_nodes(unused_nodes)

        for material_name, node_path in unused_nodes:
            material = bpy.data.materials[material_name]
            self.add_attribute_node(material, node_path)

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