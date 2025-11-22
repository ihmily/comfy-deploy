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
import json
    
from comfydeploy_utils import is_valid_url


class ComfyDeployExternalImageBatch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "param_name": ("STRING", {"multiline": False, "default": "input_image"}),
                "keep_alpha_channel": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
            },
            "optional": {
                "default_value": ("STRING", {"default": "[]", "multiline": True}),
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
    FUNCTION = "load_image_batch"
    CATEGORY = "comfy-deploy/Image"
    OUTPUT_IS_LIST = (True,)

    @staticmethod
    def load_image_batch(param_name, keep_alpha_channel, default_value=None, display_name=None, description=None):
        input_images = default_value

        return_image = None
        image_list = []
        if isinstance(input_images, str):
            if "[" in input_images and "]" in input_images:
                if '["' in input_images or f"[\"" in input_images:
                    try:
                        json_data = json.loads(input_images)
                    except json.JSONDecodeError:
                        raise RuntimeError(f"comfy-deploy: Input image: {param_name} is not a valid JSON, use default image")
                else:
                    input_images = input_images.split("[")[-1].split("]")[0]
                    json_data = [x.strip() for x in input_images.split(",")]
            else:
                json_data = [x.strip() for x in input_images.split(",")]
        else:
            json_data = input_images

        print(f"comfy-deploy: Fetching image from url: {input_images}")
        for image_url in json_data:
            retry_count = 3
            have_retry = 0
            if image_url.strip() == "" or not image_url.strip().startswith("http"):
                continue
            for i in range(retry_count):
                have_retry += 1
                try:
                    if not is_valid_url(image_url):
                        print(f"comfy-deploy: Invalid image url provided. {image_url}")
                        break
                    headers = {
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
                    }
                    response = httpx.get(image_url, timeout=60.0, headers=headers, follow_redirects=True)
                    if response.status_code == 200:
                        return_image = Image.open(BytesIO(response.content))
                        print(f"comfy-deploy: Success Load image from url: {image_url}")
                        image_list.append(return_image)
                        break
                    else:
                        print(f"comfy-deploy: Failed to retrieve the image, status code: {response.status_code}")
                except Exception as e:
                    print(f'Warning({have_retry}): comfy-deploy download image URL failed. Image URL: {image_url}. Error: {e}')

        if not image_list:
            raise RuntimeError(f'Error: comfy-deploy load image failed or empty. input_image: {input_images}')
        
        return_image_list = []
        for return_image in image_list:
            image = ImageOps.exif_transpose(return_image)
            if keep_alpha_channel:
                image = image.convert("RGBA")
            else:
                image = image.convert("RGB")
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None, ]
            return_image_list.append(image)
        return (return_image_list,)


NODE_CLASS_MAPPINGS = {"ComfyDeployExternalImageBatch": ComfyDeployExternalImageBatch}
NODE_DISPLAY_NAME_MAPPINGS = {"ComfyDeployExternalImageBatch": "External Image Batch (ComfyDeploy)"}
