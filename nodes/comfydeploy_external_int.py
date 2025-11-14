"""
@author: Hmily
@title: comfy-deploy
@nickname: comfy-deploy
@description: Easy deploy API for ComfyUI.
"""

class ComfyDeployExternalInt:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "param_name": ("STRING", {"multiline": False, "default": "input_int"}),
            },
            "optional": {
                "default_value": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647}),
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

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("int",)

    FUNCTION = "load_int"

    CATEGORY = "comfy-deploy/Number"

    def load_int(self, param_name, default_value=0, display_name=None, description=None):
        try:
            if isinstance(default_value, int):
                return_value = default_value
            else:
                return_value = int(float(default_value))
        except ValueError:
            return_value = 0
            print(f'comfy-deploy: Invalid integer value, use default value {return_value}.')
        return [return_value]


NODE_CLASS_MAPPINGS = {"ComfyDeployExternalInt": ComfyDeployExternalInt}
NODE_DISPLAY_NAME_MAPPINGS = {"ComfyDeployExternalInt": "External Integer (ComfyDeploy)"}
