
<img width="1024" height="1024" alt="Gemini_Generated_Image_sw3expsw3expsw3e" src="https://github.com/user-attachments/assets/f4306d84-9ed3-4007-a174-288bed739b0d" />


https://github.com/user-attachments/assets/705a0a50-21b6-419b-80ea-0ae4a1e1f1d1


<img width="2560" height="1080" alt="Desktop Screenshot 2025 11 22 - 10 35 02 46" src="https://github.com/user-attachments/assets/505341a1-f968-4f54-87b2-f93d565ee885" />

RNC Tutorial:

<img width="1024" height="1024" alt="Gemini_Generated_Image_vkw3rtvkw3rtvkw3_2" src="https://github.com/user-attachments/assets/18467cc7-f981-435c-8e25-438102e4a5be" />

https://youtu.be/kahQKzZo_Ek?si=Z3qyQQDgL5PSwPPL

# Rogue_Node_Communicator
# 📡 Rogue Node Communicator (RNC)

| Version | Blender Compatibility | Category | Author |
| :---: | :---: | :---: | :---: |
| **V18.1** | **4.1+** | Node / AI Utility | Makan Asnasri & Gemini |

**The ultimate bridge between Blender's nodes and AI language models.**

Rogue Node Communicator (RNC) provides robust tools to effortlessly export, analyze, and rebuild Blender node trees (Geometry, Shader, Compositor) using data formats optimized for interaction with Large Language Models (LLMs) like Gemini, ChatGPT, or Claude. Accelerate your creative workflow by letting AI build, troubleshoot, and optimize your node setups!

## ✨ Key Features

* **⚡ AI-Powered Workflow:** Seamlessly integrate powerful AI models into your procedural workflow.
* **JSON Export/Import:** Convert complex node trees into clean, machine-readable JSON for precise AI editing and rapid reconstruction in Blender. This includes support for key properties like location, size, and specific node attributes (e.g., `operation` for Math nodes, `blend_type` for Mix nodes).
* **Human-Readable Text Report:** Generate a detailed, easy-to-read text summary of your node tree to ask the AI for advice, explanations, or high-level design changes.
* **Robust Property Handling:** Enhanced support for converting Blender-native types (`Vector`, `Color`, `Material` reference names) into JSON-safe formats for export and intelligently restoring them during import.
* **Operation Normalization:** The importer intelligently translates common, human-friendly names (e e.g., "SUB", "DIV", "CROSS PRODUCT") into Blender's internal enum identifiers during the rebuild process.

## 🚀 Installation

1.  **Download:** Download the `RNC_Communicator.py` file from this repository.
2.  **Blender:** Open Blender (V4.1 or newer).
3.  **Preferences:** Go to `Edit` > `Preferences` > `Add-ons`.
4.  **Install:** Click the `Install...` button and select the downloaded `RNC_Communicator.py` file.
5.  **Enable:** Search for "Rogue Node Communicator" and check the box to enable the add-on.

## 💻 How to Use

The RNC Panel is located in the **Node Editor** sidebar (press **N** to show the sidebar), under the tab named **"RNC Panel"**.

The workflow is split into two primary use cases:

### 1. AI-Powered Editing (JSON - Machine-Readable)

Use this for precise, structural changes to your node tree.

| Operator | Icon | Description |
| :--- | :---: | :--- |
| **Export Nodes to JSON** | `EXPORT` | Copies the entire active node tree to the clipboard as a detailed JSON structure. Paste this into your AI. |
| **Import Nodes from JSON** | `IMPORT` | **DANGEROUS:** Deletes all current nodes in the tree and rebuilds it based on the JSON in your clipboard. |
| **Copy JSON Template** | `COPYDOWN` | Copies a minimal JSON structure to help the AI start from a blank canvas. |

**Example Prompt (after copying JSON):**
> *I want to modify the following Blender Geometry Node tree JSON. Please change the 'Group Input' node's 'Count' input default value to 256. Then, find the 'Noise Texture' node and change its 'scale' input to 0.5. Finally, connect the 'Vector' output of the 'Mapping' node to the 'Vector' input of the 'Noise Texture' node.*

### 2. Get Help or Give Instructions (Text - Human-Readable)

Use this to get high-level advice, explanations, or to design a new tree from a simple request.

| Operator | Icon | Description |
| :--- | :---: | :--- |
| **Explain Nodes to Text** | `QUESTION` | Generates a clean, line-by-line summary of your nodes and connections to the clipboard. Paste this into your AI to ask for a critique or explanation. |
| **Copy Text Template** | `FILE_TEXT` | Copies a simple, structured text format that you can fill out with your node design to instruct the AI. |

**Example Prompt (after copying the Text Report):**
> *Based on the following text summary of my Shader Node setup, what is the best way to add a subtle metallic flake effect without using a dedicated flake node? Please provide the JSON for the new nodes I should add.*

## ⚙️ Development Notes

This add-on features an advanced `blender_to_json_encoder` and `normalize_operation` utility to handle Blender's unique data types and enum aliases, making it one of the most robust tools for AI-driven node editing.

## 🤝 Contribution

Contributions are welcome! If you find a bug or have an idea for a new feature (especially for expanding the JSON encoding/decoding capabilities), please open an issue or submit a pull request.

## 📜 License

GPL v 3.0

<img width="2560" height="1080" alt="Desktop Screenshot 2025 11 20 - 19 04 15 01" src="https://github.com/user-attachments/assets/1b84b6f2-9958-4124-8c3d-2ac2e6a4a282" />


<img width="1024" height="1024" alt="Gemini_Generated_Image_vkw3rtvkw3rtvkw3_2" src="https://github.com/user-attachments/assets/20f11524-17b1-43a9-95fd-47691a47b266" />

https://github.com/user-attachments/assets/d4fd7333-dbe6-4851-939f-ac8c40788470
