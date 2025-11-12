# --- RNC Communicator V18 (Updated) ---
bl_info = {
    "name": "Rogue Node Communicator",
    "author": "Makan Asnasri & Gemini",
    "version": (18, 1, 0), # Incremented version for the update
    "blender": (4, 1, 0),
    "location": "Node Editor > Sidebar > RNC Panel",
    "description": "Provides tools to communicate with AI using both machine-readable JSON and human-readable text. (Improved JSON import/export for node properties)",
    "category": "Node"
}

import bpy
import json
import mathutils
from mathutils import Vector, Color, Euler

# -----------------------------------------------------------------------------
# JSON Encoder for Blender native types
# -----------------------------------------------------------------------------
def blender_to_json_encoder(obj):
    """
    Converts Blender-only objects into JSON-safe structures.
    - mathutils.Vector / Euler / Color -> lists
    - bpy_prop_array -> lists
    - Blender ID-blocks (materials, images, collections) -> name string
    - tuples/sets -> lists
    """
    # mathutils types
    try:
        if isinstance(obj, (mathutils.Vector, mathutils.Color, mathutils.Euler, mathutils.Quaternion)):
            return list(obj)
    except Exception:
        pass

    # bpy_prop_array (N-dimensional property arrays)
    try:
        if isinstance(obj, bpy.types.bpy_prop_array):
            return list(obj)
    except Exception:
        pass

    # Blender datablocks (materials, images, objects, collections, etc.)
    try:
        # check for RNA presence (typical for ID types)
        if hasattr(obj, "bl_rna") and hasattr(obj, "name"):
            # Export by name reference to keep JSON lightweight.
            return obj.name
    except Exception:
        pass

    # Common iterables
    if isinstance(obj, (set, tuple)):
        return list(obj)

    # If object has to_list method, prefer it
    if hasattr(obj, "to_list"):
        try:
            return list(obj.to_list())
        except Exception:
            pass

    # Let json raise a TypeError for anything else.
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class RNC_OT_ExportJSON(bpy.types.Operator):
    """Exports the active node tree to the clipboard as JSON"""
    bl_idname = "rnc.export_json"
    bl_label = "Export Nodes to JSON"
    bl_description = "Copies the node tree as a machine-readable JSON table. Ideal for precise AI editing and backup"

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
                "width": getattr(node, "width", None),
            }
            if hasattr(node, 'height'):
                node_info['height'] = node.height

            # Export node-specific attributes (operation, blend_type, etc.) if present
            if hasattr(node, "operation"):
                try:
                    node_info["operation"] = node.operation
                except Exception:
                    pass
            if hasattr(node, "blend_type"):
                try:
                    node_info["blend_type"] = node.blend_type
                except Exception:
                    pass

            # Inputs
            inputs_data = {}
            for inp in node.inputs:
                if hasattr(inp, 'default_value'):
                    try:
                        inputs_data[inp.name] = inp.default_value
                    except Exception:
                        try:
                            v = inp.default_value
                            if hasattr(v, "to_list"):
                                inputs_data[inp.name] = v.to_list()
                            else:
                                inputs_data[inp.name] = list(v)
                        except Exception:
                            inputs_data[inp.name] = None
            node_info['inputs'] = inputs_data

            # Outputs (some outputs have default values)
            outputs_data = {}
            for out in node.outputs:
                if hasattr(out, 'default_value'):
                    try:
                        outputs_data[out.name] = out.default_value
                    except Exception:
                        try:
                            v = out.default_value
                            if hasattr(v, "to_list"):
                                outputs_data[out.name] = v.to_list()
                            else:
                                outputs_data[out.name] = list(v)
                        except Exception:
                            outputs_data[out.name] = None
            node_info['outputs'] = outputs_data

            nodes_data.append(node_info)

        links_data = []
        for link in node_tree.links:
            try:
                link_info = {
                    "from_node": link.from_node.name,
                    "from_socket": link.from_socket.name,
                    "to_node": link.to_node.name,
                    "to_socket": link.to_socket.name
                }
            except Exception:
                continue
            links_data.append(link_info)

        data = {"nodes": nodes_data, "links": links_data}

        try:
            context.window_manager.clipboard = json.dumps(data, indent=4, default=blender_to_json_encoder)
            self.report({'INFO'}, "Node tree exported to clipboard as JSON.")
        except TypeError as e:
            self.report({'ERROR'}, f"JSON Export Failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class RNC_OT_ImportJSON(bpy.types.Operator):
    """Imports a node tree from clipboard JSON"""
    bl_idname = "rnc.import_json"
    bl_label = "Import Nodes from JSON"
    bl_description = "Deletes the current tree and rebuilds it from a JSON table in the clipboard. Use with caution!"

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
        for node in list(node_tree.nodes):
            node_tree.nodes.remove(node)

        nodes_created = {}

        # Helper: map common operation aliases to Blender internal names
        def normalize_operation(op_name, property_name="operation"):
            """
            Normalizes a human-readable operation name to Blender's internal enum identifier.
            Handles 'operation' for Math/VectorMath nodes and 'blend_type' for Mix nodes.
            """
            if not isinstance(op_name, str):
                return op_name
            
            s = op_name.strip().upper().replace(" ", "_")

            # Master Alias Map for all node operations and blend types
            alias_map = {
                # --- Math Nodes (Shader, Geometry, Compositor) ---
                "ADD": "ADD",
                "SUBTRACT": "SUBTRACT", "SUB": "SUBTRACT",
                "MULTIPLY": "MULTIPLY", "MUL": "MULTIPLY",
                "DIVIDE": "DIVIDE", "DIV": "DIVIDE",
                "SINE": "SINE", "SIN": "SINE",
                "COSINE": "COSINE", "COS": "COSINE",
                "TANGENT": "TANGENT", "TAN": "TANGENT",
                "ARCSINE": "ARCSINE", "ASIN": "ARCSINE",
                "ARCCOSINE": "ARCCOSINE", "ACOS": "ARCCOSINE",
                "ARCTANGENT": "ARCTANGENT", "ATAN": "ARCTANGENT",
                "ARCTAN2": "ARCTAN2", "ATAN2": "ARCTAN2",
                "POWER": "POWER", "POW": "POWER",
                "LOGARITHM": "LOGARITHM", "LOG": "LOGARITHM",
                "MINIMUM": "MINIMUM", "MIN": "MINIMUM",
                "MAXIMUM": "MAXIMUM", "MAX": "MAXIMUM",
                "ROUND": "ROUND",
                "LESS_THAN": "LESS_THAN", "LT": "LESS_THAN", "<": "LESS_THAN",
                "GREATER_THAN": "GREATER_THAN", "GT": "GREATER_THAN", ">": "GREATER_THAN",
                "MODULO": "MODULO", "MOD": "MODULO",
                "ABSOLUTE": "ABSOLUTE", "ABS": "ABSOLUTE",
                "EXPONENT": "EXPONENT",
                "RADIANS": "RADIANS",
                "DEGREES": "DEGREES",
                "SQRT": "SQRT", "SQUARE_ROOT": "SQRT",
                "INV_SQRT": "INV_SQRT", "INVERSE_SQUARE_ROOT": "INV_SQRT",
                "SIGN": "SIGN",
                "CEIL": "CEIL", "CEILING": "CEIL",
                "FLOOR": "FLOOR",
                "TRUNC": "TRUNC", "TRUNCATE": "TRUNC",
                "FRACT": "FRACT", "FRACTION": "FRACT",
                "MULTIPLY_ADD": "MULTIPLY_ADD", "MADD": "MULTIPLY_ADD",
                "SNAP": "SNAP",
                "WRAP": "WRAP",
                "COMPARE": "COMPARE",
                "PINGPONG": "PINGPONG",
                "SMOOTH_MIN": "SMOOTH_MIN",
                "SMOOTH_MAX": "SMOOTH_MAX",

                # --- Vector Math Nodes (Shader, Geometry, Compositor) ---
                # (Includes some from the Math list)
                "CROSS_PRODUCT": "CROSS_PRODUCT", "CROSS": "CROSS_PRODUCT",
                "PROJECT": "PROJECT",
                "REFLECT": "REFLECT",
                "REFRACT": "REFRACT",
                "FACEFORWARD": "FACEFORWARD",
                "DOT_PRODUCT": "DOT_PRODUCT", "DOT": "DOT_PRODUCT",
                "DISTANCE": "DISTANCE", "DIST": "DISTANCE",
                "LENGTH": "LENGTH", "LEN": "LENGTH",
                "SCALE": "SCALE",
                "NORMALIZE": "NORMALIZE", "NORMAL": "NORMALIZE",

                # --- Mix Nodes (ShaderNodeMix, CompositorNodeMixRGB) ---
                # Note: GeometryNodeMix is different and doesn't use blend_type
                "MIX": "MIX", "BLEND": "MIX",
                "DARKEN": "DARKEN",
                "BURN": "BURN", "COLOR_BURN": "BURN",
                "LIGHTEN": "LIGHTEN",
                "SCREEN": "SCREEN",
                "DODGE": "DODGE", "COLOR_DODGE": "DODGE",
                "OVERLAY": "OVERLAY",
                "SOFT_LIGHT": "SOFT_LIGHT",
                "LINEAR_LIGHT": "LINEAR_LIGHT",
                "DIFFERENCE": "DIFFERENCE", "DIFF": "DIFFERENCE",
                "HUE": "HUE",
                "SATURATION": "SATURATION", "SAT": "SATURATION",
                "COLOR": "COLOR",
                "VALUE": "VALUE",
                "EXCLUSION": "EXCLUSION",
            }
            return alias_map.get(s, s) # Return the mapped value, or the original if not found

        for node_info in data.get("nodes", []):
            try:
                new_node = node_tree.nodes.new(type=node_info["type"])
                new_node.name = node_info.get("name", new_node.name)
                new_node.label = node_info.get("label", "")
                loc = node_info.get("location", [0, 0])
                try:
                    new_node.location = (loc[0], loc[1])
                except Exception:
                    pass
                if "width" in node_info and hasattr(new_node, "width"):
                    try:
                        new_node.width = node_info["width"]
                    except Exception:
                        pass
                if 'height' in node_info and hasattr(new_node, 'height'):
                    try:
                        new_node.height = node_info["height"]
                    except Exception:
                        pass

                # --- ENHANCED PROPERTY RESTORATION ---
                # Restore node-specific attributes BEFORE setting inputs
                
                # Handle 'operation' for Math nodes
                if "operation" in node_info and hasattr(new_node, "operation"):
                    op_val = normalize_operation(node_info["operation"], "operation")
                    try:
                        new_node.operation = op_val
                    except TypeError:
                        print(f"[RNC] Warning: could not set operation='{op_val}' for node '{new_node.name}'. Invalid value.")
                    except Exception as e:
                        print(f"[RNC] Warning: An error occurred setting operation for '{new_node.name}': {e}")

                # Handle 'blend_type' for Mix nodes
                if "blend_type" in node_info and hasattr(new_node, "blend_type"):
                    blend_val = normalize_operation(node_info["blend_type"], "blend_type")
                    try:
                        new_node.blend_type = blend_val
                    except TypeError:
                        print(f"[RNC] Warning: could not set blend_type='{blend_val}' for node '{new_node.name}'. Invalid value.")
                    except Exception as e:
                        print(f"[RNC] Warning: An error occurred setting blend_type for '{new_node.name}': {e}")

                # Set inputs default values where possible
                for inp_name, value in node_info.get('inputs', {}).items():
                    target_inp = new_node.inputs.get(inp_name)
                    if target_inp and hasattr(target_inp, 'default_value'):
                        try:
                            if isinstance(value, str):
                                if target_inp.bl_idname.endswith("Material") or "Material" in target_inp.name:
                                    mat = bpy.data.materials.get(value)
                                    if mat:
                                        target_inp.default_value = mat
                                        continue
                            target_inp.default_value = value
                        except Exception:
                            try:
                                dv = target_inp.default_value
                                if hasattr(dv, "__len__") and hasattr(value, "__len__") and len(dv) == len(value):
                                    target_inp.default_value = value
                            except Exception:
                                pass

                # Set outputs default values where possible
                for out_name, value in node_info.get('outputs', {}).items():
                    target_out = new_node.outputs.get(out_name)
                    if target_out and hasattr(target_out, 'default_value'):
                        try:
                            target_out.default_value = value
                        except Exception:
                            try:
                                dv = target_out.default_value
                                if hasattr(dv, "__len__") and hasattr(value, "__len__") and len(dv) == len(value):
                                    target_out.default_value = value
                            except Exception:
                                pass

                nodes_created[node_info.get("name", new_node.name)] = new_node
            except Exception as e:
                self.report({'WARNING'}, f"Failed to create node '{node_info.get('name','?')}': {str(e)}")

        # Recreate links
        for link_info in data.get("links", []):
            from_node = nodes_created.get(link_info.get("from_node"))
            to_node = nodes_created.get(link_info.get("to_node"))
            if from_node and to_node:
                from_socket = from_node.outputs.get(link_info.get("from_socket"))
                to_socket = to_node.inputs.get(link_info.get("to_socket"))
                if from_socket and to_socket:
                    try:
                        node_tree.links.new(from_socket, to_socket)
                    except Exception as e:
                        print(f"[RNC] Warning: failed to create link {link_info}: {e}")

        self.report({'INFO'}, "Node tree imported from clipboard.")
        return {'FINISHED'}


class RNC_OT_CopyBaseJSON(bpy.types.Operator):
    bl_idname = "rnc.copy_base_json"; bl_label = "Copy JSON Template"
    bl_description = "Copies a minimal JSON template to start a new node tree from scratch"
    def execute(self, context):
        base_data = {
            "nodes": [
                {"name": "Group Input", "type": "NodeGroupInput", "location": [0, 0], "inputs": {}, "outputs": {}},
                {"name": "Group Output", "type": "NodeGroupOutput", "location": [400, 0], "inputs": {}, "outputs": {}}
            ],
            "links": []
        }
        context.window_manager.clipboard = json.dumps(base_data, indent=4)
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
        report_lines = []
        report_lines.append("--- NODE GROUP ANALYSIS ---")
        report_lines.append(f"Total Nodes: {len(node_tree.nodes)}\n")
        report_lines.append("--- NODES ---")
        for i, node in enumerate(node_tree.nodes):
            report_lines.append(f"\nNode {i+1}: '{node.name}' (Type: {node.bl_idname})")
            if hasattr(node, 'operation'):
                report_lines.append(f"  - Attribute: Operation = {getattr(node, 'operation', '')}")
            if hasattr(node, 'blend_type'):
                report_lines.append(f"  - Attribute: Blend Type = {getattr(node, 'blend_type', '')}")
            if node.inputs:
                report_lines.append("  - Inputs:")
                for inp in node.inputs:
                    if hasattr(inp, 'default_value'):
                        val = inp.default_value
                        if hasattr(val, 'to_list'):
                            try:
                                val = [round(v, 3) for v in val.to_list()]
                            except Exception:
                                val = str(val)
                        elif isinstance(val, bpy.types.bpy_prop_array):
                            try:
                                val = [round(v, 3) for v in list(val)]
                            except Exception:
                                val = str(val)
                        elif isinstance(val, float):
                            val = round(val, 3)
                        report_lines.append(f"    - '{inp.name}': Default = {val}")
                    else:
                        report_lines.append(f"    - '{inp.name}'")
            if node.outputs:
                report_lines.append("  - Outputs:")
                for out in node.outputs:
                    report_lines.append(f"    - '{out.name}'")
        report_lines.append("\n--- CONNECTIONS ---")
        if not node_tree.links:
            report_lines.append("No connections in this node group.")
        else:
            for i, link in enumerate(node_tree.links):
                report_lines.append(f"\nConnection {i+1}:")
                report_lines.append(f"  - From Node: '{link.from_node.name}' (Socket: '{link.from_socket.name}')")
                report_lines.append(f"  - To Node:   '{link.to_node.name}' (Socket: '{link.to_socket.name}')")
        context.window_manager.clipboard = "\n".join(report_lines)
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
    bl_label = "RNC Communicator V18.1"
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