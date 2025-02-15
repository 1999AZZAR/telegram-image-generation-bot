# helper.py
import os
import base64
import logging
from typing import Optional
import requests
from PIL import Image, ImageEnhance
from dotenv import load_dotenv

from models import ImageConfig, GenerationParams

load_dotenv()


class AuthHelper:
    def __init__(self):
        self.allowed_users = os.getenv("USER_ID", "").split(",")
        self.allowed_admins = os.getenv("ADMIN_ID", "").split(",")

    def is_user(self, user_id: str) -> bool:
        return "*" in self.allowed_users or str(user_id) in self.allowed_users

    def is_admin(self, user_id: str) -> bool:
        return "*" in self.allowed_admins or str(user_id) in self.allowed_admins


class ImageHelper:
    def __init__(self):
        self.api_key = os.getenv("STABILITY_API_KEY")
        self.output_directory = "./image"
        os.makedirs(self.output_directory, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def _add_watermark(
        self, input_path: str, output_path: str, watermark_path: Optional[str] = None
    ) -> None:
        if not watermark_path or not os.path.exists(watermark_path):
            Image.open(input_path).save(output_path)
            return

        try:
            original = Image.open(input_path)
            watermark = Image.open(watermark_path)

            # Resize watermark
            min_dimension = min(original.size)
            watermark_size = (int(min_dimension * 0.14),) * 2
            watermark = watermark.resize(watermark_size)
            watermark = watermark.convert("RGBA")

            # Apply watermark
            result = original.copy()
            position = (0, original.size[1] - watermark_size[1])

            # Adjust transparency
            alpha = watermark.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(0.25)
            watermark.putalpha(alpha)

            result.paste(watermark, position, watermark)
            result.save(output_path)
        except Exception as e:
            self.logger.error(f"Watermark error: {e}")
            original.save(output_path)

    def generate_image(self, params: GenerationParams) -> Optional[str]:
        try:
            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image",
                # "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=self._prepare_generation_params(params),
            )

            response.raise_for_status()
            data = response.json()

            # Save image
            output_path = (
                f'{self.output_directory}/txt2img_{data["artifacts"][0]["seed"]}.png'
            )
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(data["artifacts"][0]["base64"]))

            # Add watermark
            self._add_watermark(output_path, output_path, "logo.png")

            return output_path
        except Exception as e:
            self.logger.error(f"Image generation error: {e}")
            return None

    def _prepare_generation_params(self, params: GenerationParams) -> dict:
        image_config = ImageConfig()  # Instantiate ImageConfig

        generation_params = {
            "samples": 1,
            "steps": 50,
            "cfg_scale": 5.5,
            "text_prompts": [
                {"text": params.prompt, "weight": 1},
                {
                    "text": "The artwork showcases excellent anatomy with a clear, complete, and appealing depiction. It has well-proportioned and polished details, presenting a unique and balanced composition. The high-resolution image is undamaged and well-formed, conveying a healthy and natural appearance without mutations or blemishes. The positive aspect of the artwork is highlighted by its skillful framing and realistic features, including a well-drawn face and hands. The absence of signatures contributes to its seamless and authentic quality, and the depiction of straight fingers adds to its overall attractiveness.",
                    "weight": 0.3,
                },
                {
                    "text": "2 faces, 2 heads, bad anatomy, blurry, cloned face, cropped image, cut-off, deformed hands, disconnected limbs, disgusting, disfigured, draft, duplicate artifact, extra fingers, extra limb, floating limbs, gloss proportions, grain, gross proportions, long body, long neck, low-res, mangled, malformed, malformed hands, missing arms, missing limb, morbid, mutation, mutated, mutated hands, mutilated, mutilated hands, multiple heads, negative aspect, out of frame, poorly drawn, poorly drawn face, poorly drawn hands, signatures, surreal, tiling, twisted fingers, ugly",
                    "weight": -1,
                },
            ],
        }

        if params.size in image_config.SIZE_MAPPING:  # ✅ Use the instance
            height, width = image_config.SIZE_MAPPING[params.size]
            generation_params.update({"height": height, "width": width})

        if params.style != "None":
            generation_params["style_preset"] = params.style

        return generation_params
