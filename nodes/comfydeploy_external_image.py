"""
@author: Hmily
@title: comfy-deploy
@nickname: comfy-deploy
@description: Easy deploy API for ComfyUI.
"""

import folder_paths
import httpx
from PIL import Image, ImageOps
import numpy as np
import torch
from io import BytesIO
import base64
from comfydeploy_utils import is_valid_url


class ComfyDeployExternalImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "param_name": ("STRING", {"multiline": False, "default": "input_image"}),
                "keep_alpha_channel": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
            },
            "optional": {
                "default_value": ("IMAGE",),
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

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)

    FUNCTION = "load_image"

    CATEGORY = "comfy-deploy/Image"

    @staticmethod
    def load_image(param_name, keep_alpha_channel, default_value=None, display_name=None, description=None):
        input_image = param_name

        return_image = None
        if input_image and input_image.startswith('http'):
            print(f"comfy-deploy: Fetching image from url: {input_image}")

            retry_count = 3
            have_retry = 0
            for i in range(retry_count):
                have_retry += 1
                try:
                    if not is_valid_url(input_image):
                         print(f"comfy-deploy: Invalid image url provided. {input_image}")
                         return [default_value]
                    headers = {
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
                    }
                    response = httpx.get(input_image, timeout=60.0, headers=headers, follow_redirects=True)
                    if response.status_code == 200:
                        return_image = Image.open(BytesIO(response.content))
                        print(f"comfy-deploy: Success Load image from url: {input_image}")
                        break
                    else:
                        print(f"comfy-deploy: Failed to retrieve the image, status code: {response.status_code}")
                except Exception as e:
                    print(f'Warning({have_retry}): comfy-deploy download image URL failed. Image URL: {input_image}. Error: {e}')

        elif input_image and input_image.startswith('data:image/png;base64,') or input_image.startswith(
                'data:image/jpeg;base64,') or input_image.startswith('data:image/jpg;base64,'):

            print("Decoding base64 image")
            base64_image = input_image[input_image.find(",") + 1:]
            decoded_image = base64.b64decode(base64_image)
            return_image = Image.open(BytesIO(decoded_image))

        else:
            print(f'comfy-deploy: Input image: {param_name} is empty, use default image')
            return [default_value]

        if not return_image:
            raise RuntimeError(f'Error: comfy-deploy load image failed. input_image: {input_image}')

        image = ImageOps.exif_transpose(return_image)
        if keep_alpha_channel:
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None, ]
        return [image]





NODE_CLASS_MAPPINGS = {"ComfyDeployExternalImage": ComfyDeployExternalImage}
NODE_DISPLAY_NAME_MAPPINGS = {"ComfyDeployExternalImage": "External Image (ComfyDeploy)"}
