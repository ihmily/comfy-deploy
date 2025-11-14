"""
@author: Hmily
@title: comfy-deploy
@nickname: comfy-deploy
@description: Easy deploy API for ComfyUI.
"""

class ComfyDeployExternalText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "param_name": ("STRING", {"multiline": False, "default": "input_text"}),
            },
            "optional": {
                "default_value": ("STRING", {"multiline": True, "default": ""}),
                "display_name": (
                    "STRING",
                    {"multiline": False, "default": ""},
                ),
                "description": (
                    "STRING",
                    {"multiline": True, "default": ""},
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    FUNCTION = "load_text"

    CATEGORY = "comfy-deploy/Text"

    def load_text(self, param_name, default_value="", display_name=None, description=None):
        return [str(default_value)]


NODE_CLASS_MAPPINGS = {"ComfyDeployExternalText": ComfyDeployExternalText}
NODE_DISPLAY_NAME_MAPPINGS = {"ComfyDeployExternalText": "External Text (ComfyDeploy)"}
