import os
import base64
import logging
from typing import Optional
import requests
from PIL import Image, ImageEnhance
from dotenv import load_dotenv

from models import ImageConfig, GenerationParams, ReimagineParams

MAX_PIXELS = 1_048_576  # Stability AI's max pixel limit
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
        image_config = ImageConfig()  # Load predefined size mappings and styles

        generation_params = {
            "samples": 1,
            "steps": 50,
            "cfg_scale": 5.5,
            "text_prompts": [
                {"text": params.prompt, "weight": 1},  # User's main prompt
                {
                    "text": "The artwork showcases excellent anatomy with a clear, complete, and appealing depiction. "
                    "It has well-proportioned and polished details, presenting a unique and balanced composition. "
                    "The high-resolution image is undamaged and well-formed, conveying a healthy and natural appearance "
                    "without mutations or blemishes. The positive aspect of the artwork is highlighted by its skillful "
                    "framing and realistic features, including a well-drawn face and hands. The absence of signatures "
                    "contributes to its seamless and authentic quality, and the depiction of straight fingers adds to "
                    "its overall attractiveness.",
                    "weight": 0.3,  # Positive reinforcement for high-quality results
                },
                {
                    "text": "2 faces, 2 heads, bad anatomy, blurry, cloned face, cropped image, cut-off, deformed hands, "
                    "disconnected limbs, disgusting, disfigured, draft, duplicate artifact, extra fingers, extra limb, "
                    "floating limbs, gloss proportions, grain, gross proportions, long body, long neck, low-res, mangled, "
                    "malformed, malformed hands, missing arms, missing limb, morbid, mutation, mutated, mutated hands, "
                    "mutilated, mutilated hands, multiple heads, negative aspect, out of frame, poorly drawn, poorly drawn face, "
                    "poorly drawn hands, signatures, surreal, tiling, twisted fingers, ugly",
                    "weight": -1,  # Negative prompt to avoid unwanted artifacts
                },
            ],
        }

        # Set image dimensions based on user selection
        if params.size in image_config.SIZE_MAPPING:
            height, width = image_config.SIZE_MAPPING[params.size]
            generation_params.update({"height": height, "width": width})

        # Apply style preset if selected
        if params.style != "None":
            generation_params["style_preset"] = params.style

        # **Handle Control-Based Image Generation**
        if params.control_image:
            generation_params["image"] = params.control_image
            generation_params[
                "host"
            ] = "https://api.stability.ai/v2beta/stable-image/control/style"
            generation_params["fidelity"] = 0.9
        else:
            generation_params[
                "host"
            ] = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image"

        return generation_params

    def upscale_image(self, image_path: str, output_format: str) -> str:
        """Sends the image to Stability AI for upscaling, resizing it first if too large."""
        host = "https://api.stability.ai/v2beta/stable-image/upscale/fast"
        params = {"output_format": output_format}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "image/*",
        }

        try:
            self.logger.info(f"🚀 Starting upscaling process for: {image_path}")

            # ✅ Step 1: Open image and check size
            with Image.open(image_path) as img:
                width, height = img.size
                total_pixels = width * height
                self.logger.info(
                    f"📏 Original Image Size: {width}x{height} ({total_pixels} pixels)"
                )

                # ✅ Step 2: Resize if needed
                if total_pixels > MAX_PIXELS:
                    scale_factor = (
                        MAX_PIXELS / total_pixels
                    ) ** 0.5  # Keep aspect ratio
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    self.logger.info(f"🔄 Resizing image to: {new_width}x{new_height}")

                    img = img.resize((new_width, new_height), Image.LANCZOS)

                    # Save the resized image as a temporary file
                    resized_path = (
                        f"{self.output_directory}/resized_temp.{output_format}"
                    )
                    img.save(resized_path)
                    image_path = resized_path  # Use the resized image for upscaling

            # ✅ Step 3: Send the image to Stability AI
            with open(image_path, "rb") as image_file:
                self.logger.info("📡 Sending upscale request to Stability AI...")
                response = requests.post(
                    host,
                    headers=headers,
                    files={"image": image_file},
                    data=params,
                    timeout=120,
                )

            self.logger.info(f"✅ Stability AI Response: {response.status_code}")

            response.raise_for_status()
            output_image = response.content

            # ✅ Step 4: Save upscaled image with correct filename
            upscaled_path = f"{self.output_directory}/upscalled.{output_format}"
            with open(upscaled_path, "wb") as f:
                f.write(output_image)

            self.logger.info(f"✅ Upscaled image saved as: {upscaled_path}")
            return upscaled_path

        except requests.exceptions.Timeout:
            self.logger.error("⏳ Upscaling request timed out.")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"❌ HTTP Error in upscaling: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            self.logger.error(f"❌ General Error in upscaling: {e}")
            return None

    def reimagine_image(self, params: ReimagineParams) -> Optional[str]:
        """Sends an image to Stability AI's reimagine API for structural transformation."""
        try:
            host = "https://api.stability.ai/v2beta/stable-image/control/structure"

            request_params = {
                "control_strength": params.control_strength,
                "seed": params.seed,
                "output_format": params.output_format,
                "prompt": params.prompt,
                "negative_prompt": params.negative_prompt,
            }

            if params.style != "None":
                request_params["style_preset"] = params.style  # Apply style if selected

            response = requests.post(
                host,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "image/*",
                },
                files={"image": open(params.control_image, "rb")},
                data=request_params,
            )

            response.raise_for_status()
            output_image = response.content

            # Save the generated image
            filename, _ = os.path.splitext(os.path.basename(params.control_image))
            output_path = f"{self.output_directory}/reimagined_{filename}_{params.seed}.{params.output_format}"
            with open(output_path, "wb") as f:
                f.write(output_image)

            self.logger.info(f"✅ Reimagined image saved as: {output_path}")
            return output_path

        except requests.exceptions.Timeout:
            self.logger.error("⏳ Reimagine request timed out.")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"❌ HTTP Error in reimagining: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            self.logger.error(f"❌ General Error in reimagine_image: {e}")
            return None
