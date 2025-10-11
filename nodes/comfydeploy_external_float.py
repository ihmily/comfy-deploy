"""
@author: Hmily
@title: comfy-deploy
@nickname: comfy-deploy
@description: Easy deploy API for ComfyUI.
"""

class ComfyDeployExternalFloat:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "param_name": ("STRING", {"multiline": False, "default": "input_float"}),
            },
            "optional": {
                "default_value": ("FLOAT", {"default": 0.0, "min": -3.402823e+38, "max": 3.402823e+38, "step": 0.01}),
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

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("float",)

    FUNCTION = "load_float"

    CATEGORY = "comfy-deploy/Number"

    def load_float(self, param_name, default_value=0.0, display_name=None, description=None):
        try:
            if isinstance(param_name, str) and param_name.strip():
                return_value = float(param_name)
            else:
                print('comfy-deploy: Input float is empty or invalid, use default value')
                return_value = default_value
        except ValueError:
            print('comfy-deploy: Invalid float value, use default value')
            return_value = default_value
        
        return [return_value]


NODE_CLASS_MAPPINGS = {"ComfyDeployExternalFloat": ComfyDeployExternalFloat}
NODE_DISPLAY_NAME_MAPPINGS = {"ComfyDeployExternalFloat": "External Float (ComfyDeploy)"}
