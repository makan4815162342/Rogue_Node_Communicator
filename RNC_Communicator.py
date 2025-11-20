# --- RNC Communicator V22.1 (Blender 5.0 Ready) ---
bl_info = {
    "name": "Rogue Node Communicator",
    "author": "Makan Asnasri & Gemini",
    "version": (22, 1, 0),
    "blender": (4, 2, 0), # Targeted for 4.2 LTS and 5.0+
    "location": "Node Editor > Sidebar > RNC Panel",
    "description": "Future-proofed AI Bridge. Fixes Mix nodes, Socket Naming bugs, and supports dynamic properties.",
    "category": "Node"
}

import bpy
import json
import mathutils
from mathutils import Vector, Color, Euler

# -----------------------------------------------------------------------------
# JSON Encoder
# -----------------------------------------------------------------------------
def blender_to_json_encoder(obj):
    if isinstance(obj, (mathutils.Vector, mathutils.Color, mathutils.Euler, mathutils.Quaternion)):
        return list(obj)
    if isinstance(obj, bpy.types.bpy_prop_array):
        return list(obj)
    if hasattr(obj, "bl_rna") and hasattr(obj, "name"):
        return obj.name
    if isinstance(obj, (set, tuple)):
        return list(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# -----------------------------------------------------------------------------
# Smart Property Engine (The V22 Core)
# -----------------------------------------------------------------------------
def get_node_properties(node):
    """
    Dynamically extracts settings (Dropdowns, Checkboxes, Sliders) 
    compatible with any Blender version (4.x, 5.x).
    """
    props = {}
    for prop_name in node.bl_rna.properties.keys():
        # Skip internal blender properties
        if prop_name in {'rna_type', 'name', 'label', 'location', 'width', 'height', 'inputs', 'outputs', 'parent', 'select', 'dimensions', 'color', 'is_active_output'}:
            continue
        try:
            val = getattr(node, prop_name)
            if isinstance(val, (int, float, str, bool)):
                props[prop_name] = val
            elif hasattr(val, "to_list"):
                props[prop_name] = list(val)
            elif isinstance(val, (Vector, Color, Euler)):
                props[prop_name] = list(val)
        except Exception:
            pass
    return props

def set_node_properties(node, props_dict):
    """
    Sets properties intelligently. Crucial for Mix nodes (Float vs Color).
    """
    for prop_name, value in props_dict.items():
        if hasattr(node, prop_name):
            try:
                attr = getattr(node, prop_name)
                if isinstance(attr, int): setattr(node, prop_name, int(value))
                elif isinstance(attr, float): setattr(node, prop_name, float(value))
                elif isinstance(attr, str): setattr(node, prop_name, str(value))
                else: setattr(node, prop_name, value)
            except Exception:
                pass

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class RNC_OT_ExportJSON(bpy.types.Operator):
    """Exports the active node tree to the clipboard as JSON"""
    bl_idname = "rnc.export_json"
    bl_label = "Export Nodes to JSON"
    bl_description = "Copies the node tree using Unique Identifiers (V22 Standard)"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and space.type == 'NODE_EDITOR' and hasattr(space, 'edit_tree') and space.edit_tree is not None

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        nodes_data = []
        for node in node_tree.nodes:
            node_info = {
                "name": node.name,
                "label": node.label,
                "type": node.bl_idname,
                "location": [node.location.x, node.location.y],
                "width": getattr(node, "width", 200),
                # V22: Use Smart Property Extraction
                "properties": get_node_properties(node)
            }
            
            # Inputs: Use Identifier (Unique) instead of Name
            inputs_data = {}
            for inp in node.inputs:
                if not inp.is_linked and hasattr(inp, 'default_value'):
                    try:
                        val = inp.default_value
                        if hasattr(val, "to_list"):
                            inputs_data[inp.identifier] = list(val)
                        elif isinstance(val, (Vector, Color, bpy.types.bpy_prop_array)):
                            inputs_data[inp.identifier] = list(val)
                        else:
                            inputs_data[inp.identifier] = val
                    except:
                        inputs_data[inp.identifier] = None
            node_info['inputs'] = inputs_data

            # Outputs: Store identifiers for linking
            node_info['outputs'] = [out.identifier for out in node.outputs]

            nodes_data.append(node_info)

        links_data = []
        for link in node_tree.links:
            if link.is_valid:
                links_data.append({
                    "from_node": link.from_node.name,
                    "from_socket": link.from_socket.identifier, # V22: Unique ID
                    "to_node": link.to_node.name,
                    "to_socket": link.to_socket.identifier      # V22: Unique ID
                })

        data = {"version": "22.1", "nodes": nodes_data, "links": links_data}

        try:
            context.window_manager.clipboard = json.dumps(data, indent=2, default=blender_to_json_encoder)
            self.report({'INFO'}, "Node tree exported to clipboard (V22 Format).")
        except TypeError as e:
            self.report({'ERROR'}, f"JSON Export Failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class RNC_OT_ImportJSON(bpy.types.Operator):
    """Imports a node tree from clipboard JSON"""
    bl_idname = "rnc.import_json"
    bl_label = "Import Nodes from JSON"
    bl_description = "Rebuilds tree. Handles Mix Nodes, Musgrave conversion, and Duplicate Names."

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and space.type == 'NODE_EDITOR' and hasattr(space, 'edit_tree') and space.edit_tree is not None

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        try:
            data = json.loads(context.window_manager.clipboard)
        except json.JSONDecodeError:
            self.report({'ERROR'}, "Invalid JSON in clipboard.")
            return {'CANCELLED'}

        # Clear current nodes
        node_tree.nodes.clear()
        nodes_created = {}

        for n_data in data.get("nodes", []):
            node_type = n_data["type"]
            
            # Blender 4.1+ Fix: Convert Musgrave to Noise
            if "Musgrave" in node_type and not hasattr(bpy.types, node_type):
                node_type = "ShaderNodeTexNoise"
                self.report({'WARNING'}, "Converted Musgrave to Noise (Blender 4.1+)")

            try:
                new_node = node_tree.nodes.new(type=node_type)
            except Exception:
                self.report({'WARNING'}, f"Node type '{node_type}' unknown. Skipping.")
                continue

            new_node.name = n_data.get("name", new_node.name)
            new_node.label = n_data.get("label", "")
            loc = n_data.get("location", [0, 0])
            new_node.location = (loc[0], loc[1])
            if "width" in n_data: new_node.width = n_data["width"]

            # V22: Set Properties BEFORE inputs (Fixes Mix Node sockets)
            if "properties" in n_data:
                set_node_properties(new_node, n_data["properties"])
            # Legacy V18 Support
            elif "operation" in n_data:
                 set_node_properties(new_node, {"operation": n_data["operation"]})
            elif "blend_type" in n_data:
                 set_node_properties(new_node, {"blend_type": n_data["blend_type"]})

            # V22: Set Inputs using Identifiers (Fixes Duplicate Name Bug)
            for ident, val in n_data.get('inputs', {}).items():
                if val is not None:
                    socket = None
                    # 1. Try Exact Identifier Match
                    for inp in new_node.inputs:
                        if inp.identifier == ident:
                            socket = inp
                            break
                    # 2. Fallback to Name (Legacy V18 JSON)
                    if not socket:
                        socket = new_node.inputs.get(ident)

                    if socket:
                        try:
                            # Handle Material Pointers
                            if "Material" in ident and isinstance(val, str):
                                mat = bpy.data.materials.get(val)
                                if mat: socket.default_value = mat
                            # Handle Float vs List mismatch
                            elif isinstance(val, list) and isinstance(socket.default_value, float):
                                socket.default_value = val[0]
                            else:
                                socket.default_value = val
                        except Exception:
                            pass

            nodes_created[new_node.name] = new_node

        # Recreate links
        for link_info in data.get("links", []):
            src = nodes_created.get(link_info.get("from_node"))
            dst = nodes_created.get(link_info.get("to_node"))
            if src and dst:
                # V22: Match by Identifier
                s_sock = next((s for s in src.outputs if s.identifier == link_info.get("from_socket")), None)
                d_sock = next((s for s in dst.inputs if s.identifier == link_info.get("to_socket")), None)
                
                # V18 Fallback: Match by Name
                if not s_sock: s_sock = src.outputs.get(link_info.get("from_socket"))
                if not d_sock: d_sock = dst.inputs.get(link_info.get("to_socket"))

                if s_sock and d_sock:
                    try:
                        node_tree.links.new(s_sock, d_sock)
                    except Exception:
                        pass

        self.report({'INFO'}, "Node tree imported (V22 Engine).")
        return {'FINISHED'}


class RNC_OT_CopyBaseJSON(bpy.types.Operator):
    bl_idname = "rnc.copy_base_json"; bl_label = "Copy JSON Template"
    bl_description = "Copies a minimal JSON template to start a new node tree from scratch"
    def execute(self, context):
        base_data = {
            "version": "22.1",
            "nodes": [
                {"name": "Group Input", "type": "NodeGroupInput", "location": [-200, 0], "properties": {}, "inputs": {}},
                {"name": "Group Output", "type": "NodeGroupOutput", "location": [200, 0], "properties": {}, "inputs": {}}
            ],
            "links": []
        }
        context.window_manager.clipboard = json.dumps(base_data, indent=2)
        self.report({'INFO'}, "Base JSON template copied to clipboard.")
        return {'FINISHED'}


class RNC_OT_ExplainText(bpy.types.Operator):
    bl_idname = "rnc.explain_text"; bl_label = "Explain Nodes to Text"
    bl_description = "Creates a detailed, human-readable text report of the node tree on the clipboard"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and space.type == 'NODE_EDITOR' and hasattr(space, 'edit_tree') and space.edit_tree is not None

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        lines = [f"--- NODE ANALYSIS (Blender {bpy.app.version_string}) ---"]
        
        for node in node_tree.nodes:
            lines.append(f"\nNode: '{node.name}' ({node.bl_idname})")
            
            # Use V22 Smart Properties for text explanation too
            props = get_node_properties(node)
            if props:
                lines.append(f"  Settings: {json.dumps(props, default=str)}")
                
            if node.inputs:
                lines.append("  Inputs:")
                for inp in node.inputs:
                    if inp.is_linked:
                        lines.append(f"    - {inp.name} <--- {inp.links[0].from_node.name}")
                    elif hasattr(inp, 'default_value'):
                        val = inp.default_value
                        if isinstance(val, float): val = round(val, 3)
                        elif hasattr(val, "__len__"): val = [round(v,3) for v in val]
                        lines.append(f"    - {inp.name}: {val}")

        lines.append("\n--- CONNECTIONS ---")
        for link in node_tree.links:
             lines.append(f"'{link.from_node.name}' -> '{link.to_node.name}'")
             
        context.window_manager.clipboard = "\n".join(lines)
        self.report({'INFO'}, "Human-readable report copied to clipboard.")
        return {'FINISHED'}


class RNC_OT_CopyHumanTemplate(bpy.types.Operator):
    bl_idname = "rnc.copy_human_template"; bl_label = "Copy Text Template"
    bl_description = "Copies a simple text template to write instructions for an AI"
    def execute(self, context):
        template = """--- NODES ---\n\nNode 1: 'Group Input' (Type: NodeGroupInput)\n\nNode 2: 'My New Node' (Type: GeometryNodeMeshCube)\n  - Inputs:\n    - 'Size': Default = [1.0, 1.0, 1.0]\n\nNode 3: 'Group Output' (Type: NodeGroupOutput)\n\n\n--- CONNECTIONS ---\n\nConnection 1:\n  - From Node: 'My New Node' (Socket: 'Mesh')\n  - To Node:   'Group Output' (Socket: 'Geometry')\n"""
        context.window_manager.clipboard = template
        self.report({'INFO'}, "Human-readable template copied to clipboard.")
        return {'FINISHED'}


class RNC_PT_Panel(bpy.types.Panel):
    bl_label = "RNC Communicator V22.1"
    bl_idname = "RNC_PT_Panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "RNC Panel"

    def draw(self, context):
        layout = self.layout
        guide_box = layout.box()
        guide_box.label(text="Workflow Guide", icon='INFO')
        guide_box.label(text="Location: Node Editor > Sidebar (N) > 'RNC Panel' tab")
        guide_box.separator()
        guide_box.label(text="1. AI-Powered Editing (JSON):", icon='SCRIPTPLUGINS')
        col_json = guide_box.column(align=True)
        col_json.label(text="   - Use 'Export to JSON' to copy your node tree.")
        col_json.label(text="   - Paste the JSON to an AI and ask for specific changes.")
        col_json.label(text="   - Copy the AI's modified JSON.")
        col_json.label(text="   - Use 'Import from JSON' to build the new tree.")
        guide_box.separator()
        guide_box.label(text="2. Get Help or Give Instructions (Text):", icon='TEXT')
        col_text = guide_box.column(align=True)
        col_text.label(text="   - Use 'Explain Nodes to Text' to understand a setup.")
        col_text.label(text="   - Paste the text to an AI to ask for advice.")
        col_text.label(text="   - Use 'Copy Text Template' to write your own instructions.")
        layout.separator()
        json_box = layout.box()
        json_box.label(text="Machine-Readable (JSON)", icon='SCRIPTPLUGINS')
        json_box.operator(RNC_OT_ExportJSON.bl_idname, icon='EXPORT')
        json_box.operator(RNC_OT_ImportJSON.bl_idname, icon='IMPORT')
        json_box.operator(RNC_OT_CopyBaseJSON.bl_idname, icon='COPYDOWN')
        layout.separator()
        human_box = layout.box()
        human_box.label(text="Human-Readable (Text)", icon='TEXT')
        human_box.operator(RNC_OT_ExplainText.bl_idname, icon='QUESTION')
        human_box.operator(RNC_OT_CopyHumanTemplate.bl_idname, icon='FILE_TEXT')


classes = (RNC_OT_ExportJSON, RNC_OT_ImportJSON, RNC_OT_CopyBaseJSON, RNC_OT_ExplainText, RNC_OT_CopyHumanTemplate, RNC_PT_Panel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

# Allow running inside Blender text editor for quick reload
if __name__ == "__main__":
    register()