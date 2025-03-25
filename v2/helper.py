import os
import base64
import logging
import time
from typing import Optional
import requests
from PIL import Image, ImageEnhance
from dotenv import load_dotenv

from models import ImageConfig, GenerationParams, ReimagineParams, UnCropParams

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

        # Watermark control (default: enabled)
        self.watermark_enabled = (
            os.getenv("WATERMARK_ENABLED", "true").lower() == "true"
        )

    def set_watermark_status(self, status: bool):
        """Allows admin to enable or disable watermarking."""
        self.watermark_enabled = status
        os.environ["WATERMARK_ENABLED"] = "true" if status else "false"
        self.logger.info(
            f"Watermark status changed to: {'enabled' if status else 'disabled'}"
        )

    def _add_watermark(
        self, input_path: str, output_path: str, watermark_path: Optional[str] = None
    ):
        """Applies watermark only if enabled."""
        if (
            not self.watermark_enabled
            or not watermark_path
            or not os.path.exists(watermark_path)
        ):
            Image.open(input_path).save(output_path)
            return

        try:
            self.logger.info(f"Applying watermark to {input_path}")
            original = Image.open(input_path)
            watermark = Image.open(watermark_path)

            min_dimension = min(original.size)
            watermark_size = (int(min_dimension * 0.14),) * 2
            watermark = watermark.resize(watermark_size)
            watermark = watermark.convert("RGBA")

            result = original.copy()
            position = (0, original.size[1] - watermark_size[1])

            alpha = watermark.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(0.25)
            watermark.putalpha(alpha)

            result.paste(watermark, position, watermark)
            result.save(output_path)
            self.logger.info(f"Watermark applied successfully to {output_path}")
        except Exception as e:
            self.logger.error(f"Watermark error: {e}", exc_info=True)
            original.save(output_path)

    def generate_image(self, params: GenerationParams) -> Optional[str]:
        try:
            self.logger.info(f"Generating image with prompt: {params.prompt}")
            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=self._prepare_generation_params(params),
            )

            response.raise_for_status()
            data = response.json()

            output_path = (
                f'{self.output_directory}/txt2img_{data["artifacts"][0]["seed"]}.png'
            )
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(data["artifacts"][0]["base64"]))

            self._add_watermark(output_path, output_path, "logo.png")
            self.logger.info(f"Image generated and saved at {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Image generation error: {e}", exc_info=True)
            return None

    def generate_image_v2(
        self,
        prompt: str,
        output_format: str = "png",
        image: Optional[str] = None,
        strength: Optional[float] = None,  # Add strength parameter
        aspect_ratio: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generates an image using the new Stability AI v2beta endpoint.

        Args:
            prompt (str): The text prompt for image generation.
            output_format (str): The format of the output image (e.g., "png", "webp").
            image (Optional[str]): Path to the image to use as the starting point.
            strength (Optional[float]): Controls the influence of the input image on the output (required if image is provided).
            aspect_ratio (Optional[str]): The aspect ratio of the output image.

        Returns:
            Optional[str]: Path to the generated image, or None if generation fails.
        """
        try:
            self.logger.info(f"Generating image with prompt: {prompt}")

            # Prepare the request data
            data = {
                "prompt": prompt,  # Fix typo: "prompt" instead of "prompt"
                "output_format": output_format,
            }

            # Add optional parameters if provided
            if aspect_ratio:
                data["aspect_ratio"] = aspect_ratio

            # Add the default negative prompt
            data["negative_prompt"] = (
                "bad anatomy, blurry, cloned face, cropped image, cut-off, deformed hands, "
                "disconnected limbs, disgusting, disfigured, draft, duplicate artifact, extra fingers, extra limb, "
                "floating limbs, gloss proportions, grain, gross proportions, long body, long neck, low-res, mangled, "
                "malformed, malformed hands, missing arms, missing limb, morbid, mutation, mutated, mutated hands, "
                "mutilated, mutilated hands, multiple heads, negative aspect, out of frame, poorly drawn, poorly drawn face, "
                "poorly drawn hands, signatures, surreal, tiling, twisted fingers, ugly"
            )

            # Prepare the files dictionary
            files = {"none": ""}  # Required by the API, but no file is needed
            if image:
                # Resize the image if it exceeds MAX_PIXELS
                with Image.open(image) as img:
                    width, height = img.size
                    total_pixels = width * height
                    self.logger.info(
                        f"📏 Original Image Size: {width}x{height} ({total_pixels} pixels)"
                    )

                    # Resize if needed
                    if total_pixels > MAX_PIXELS:
                        scale_factor = (
                            MAX_PIXELS / total_pixels
                        ) ** 0.5  # Keep aspect ratio
                        new_width = int(width * scale_factor)
                        new_height = int(height * scale_factor)
                        self.logger.info(
                            f"🔄 Resizing image to: {new_width}x{new_height}"
                        )

                        img = img.resize((new_width, new_height), Image.LANCZOS)

                        # Save the resized image as a temporary file
                        resized_path = (
                            f"{self.output_directory}/resized_temp.{output_format}"
                        )
                        img.save(resized_path)
                        image = resized_path  # Use the resized image for generation

                files["image"] = open(image, "rb")
                if strength is None:
                    strength = 0.75  # Default strength value if not provided
                data["strength"] = strength  # Add strength parameter

            # Send the request to the new endpoint
            response = requests.post(
                "https://api.stability.ai/v2beta/stable-image/generate/ultra",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "image/*",
                },
                files=files,  # Send files here
                data=data,  # Send non-file data here
            )

            response.raise_for_status()

            # Save the generated image
            output_path = (
                f"{self.output_directory}/txt2img_v2_{int(time.time())}.{output_format}"
            )
            with open(output_path, "wb") as f:
                f.write(response.content)

            # Add watermark if enabled
            self._add_watermark(output_path, output_path, "logo.png")

            self.logger.info(f"Image generated and saved at {output_path}")
            return output_path

        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"HTTP Error in image generation: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            self.logger.error(f"Image generation error: {e}", exc_info=True)
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

    def upscale_image(
        self,
        image_path: str,
        output_format: str,
        method: str = "fast",
        prompt: str = "",
        negative_prompt: str = "",
        creativity: float = 0.35,
        style_preset: str = "None",
    ) -> str:
        """Sends the image to Stability AI for upscaling, resizing it first if too large."""
        host = f"https://api.stability.ai/v2beta/stable-image/upscale/{method}"
        params = {
            "output_format": output_format,
        }

        # Add additional parameters for conservative and creative modes
        if method in ["conservative", "creative"]:
            params.update(
                {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "creativity": creativity,
                }
            )
            if method == "creative" and style_preset != "None":
                params["style_preset"] = style_preset

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json" if method == "creative" else "image/*",
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

            if method == "creative":
                # Handle creative upscaling (asynchronous workflow)
                if response.status_code != 200:
                    self.logger.error(f"❌ Error in upscaling request: {response.text}")
                    return None

                generation_id = response.json().get("id")
                if not generation_id:
                    self.logger.error("❌ No generation ID found in the response.")
                    return None

                self.logger.info(f"🔍 Generation ID: {generation_id}")

                # ✅ Step 4: Poll the results endpoint to retrieve the final image
                results_url = f"https://api.stability.ai/v2beta/results/{generation_id}"
                headers["Accept"] = "application/json"  # We expect JSON response

                while True:
                    self.logger.info("🔄 Polling for results...")
                    response = requests.get(results_url, headers=headers, timeout=120)

                    if response.status_code == 202:
                        # Generation is still in progress, wait and retry
                        self.logger.info(
                            "⏳ Generation in progress, retrying in 10 seconds..."
                        )
                        time.sleep(10)
                    elif response.status_code == 200:
                        # Generation is complete, check if the image is ready
                        result = response.json()
                        if result.get("status") == "succeeded":
                            self.logger.info("✅ Generation complete!")
                            image_url = result.get("output", [{}])[0].get("url")
                            if not image_url:
                                self.logger.error(
                                    "❌ No image URL found in the response."
                                )
                                return None

                            # Download the image
                            self.logger.info(f"📥 Downloading image from: {image_url}")
                            image_response = requests.get(image_url, timeout=120)
                            if image_response.status_code != 200:
                                self.logger.error(
                                    f"❌ Error downloading image: {image_response.text}"
                                )
                                return None

                            # ✅ Step 5: Save upscaled image with correct filename
                            upscaled_path = f"{self.output_directory}/upscaled_{method}.{output_format}"
                            with open(upscaled_path, "wb") as f:
                                f.write(image_response.content)

                            # Add watermark
                            self._add_watermark(
                                upscaled_path, upscaled_path, "logo.png"
                            )

                            self.logger.info(
                                f"✅ Upscaled image saved as: {upscaled_path}"
                            )
                            return upscaled_path
                        else:
                            self.logger.error(
                                f"❌ Generation failed with status: {result.get('status')}"
                            )
                            return None
                    else:
                        self.logger.error(
                            f"❌ Error in results request: {response.text}"
                        )
                        return None
            else:
                # Handle conservative and fast upscaling (synchronous workflow)
                if response.status_code != 200:
                    self.logger.error(f"❌ Error in upscaling request: {response.text}")
                    return None

                # ✅ Step 4: Save upscaled image with correct filename
                upscaled_path = (
                    f"{self.output_directory}/upscaled_{method}.{output_format}"
                )
                with open(upscaled_path, "wb") as f:
                    f.write(response.content)

                # Add watermark
                self._add_watermark(upscaled_path, upscaled_path, "logo.png")

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
            if params.method == "sketch":
                host = "https://api.stability.ai/v2beta/stable-image/control/sketch"

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

            # Add watermark
            self._add_watermark(output_path, output_path, "logo.png")

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

    def uncrop_image(self, params: UnCropParams) -> Optional[str]:
        """Performs outpainting (uncrop) on an image using Stability AI API."""
        try:
            # First, check and resize the original image if needed
            with Image.open(params.image_path) as img:
                original_width, original_height = img.size
                original_pixels = original_width * original_height

                # Resize if original image exceeds maximum pixel limit
                if original_pixels > MAX_PIXELS:
                    scale_factor = (MAX_PIXELS / original_pixels) ** 0.5
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)

                    self.logger.info(
                        f"Resizing original image from {original_width}x{original_height} "
                        f"to {new_width}x{new_height} to fit API limits"
                    )

                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    resized_path = f"{self.output_directory}/resized_{os.path.basename(params.image_path)}"
                    img.save(resized_path)
                    params.image_path = resized_path
                    original_width, original_height = new_width, new_height

                original_ratio = original_width / original_height

                # Parse target aspect ratio
                try:
                    ratio_parts = params.target_aspect_ratio.split(":")
                    target_ratio = float(ratio_parts[0]) / float(ratio_parts[1])
                except:
                    self.logger.error(
                        f"Invalid aspect ratio: {params.target_aspect_ratio}"
                    )
                    return None

                # Calculate needed outpaint amounts
                if target_ratio > original_ratio:
                    # Need to expand horizontally
                    new_width = original_height * target_ratio
                    left = int((new_width - original_width) / 2)
                    right = left
                    up = 0
                    down = 0
                else:
                    # Need to expand vertically
                    new_height = original_width / target_ratio
                    up = int((new_height - original_height) / 2)
                    down = up
                    left = 0
                    right = 0

                # Ensure we don't exceed API limits (1024px per side)
                max_expansion = 1024
                left = min(left, max_expansion)
                right = min(right, max_expansion)
                up = min(up, max_expansion)
                down = min(down, max_expansion)

                # Also ensure the final image doesn't exceed maximum pixels
                final_width = original_width + left + right
                final_height = original_height + up + down
                if final_width * final_height > MAX_PIXELS:
                    scale_factor = (MAX_PIXELS / (final_width * final_height)) ** 0.5
                    left = int(left * scale_factor)
                    right = int(right * scale_factor)
                    up = int(up * scale_factor)
                    down = int(down * scale_factor)

                    self.logger.info(
                        f"Reducing outpaint amounts to fit API limits: "
                        f"left={left}, right={right}, up={up}, down={down}"
                    )

                self.logger.info(
                    f"Outpainting with: left={left}, right={right}, up={up}, down={down}"
                )

            host = "https://api.stability.ai/v2beta/stable-image/edit/outpaint"

            request_params = {
                "left": left,
                "right": right,
                "up": up,
                "down": down,
                "prompt": params.prompt,
                "creativity": params.creativity,
                "seed": params.seed,
                "output_format": params.output_format,
            }

            with open(params.image_path, "rb") as image_file:
                response = requests.post(
                    host,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "image/*",
                    },
                    files={"image": image_file},
                    data=request_params,
                    timeout=120,
                )

            response.raise_for_status()

            # Check for NSFW classification
            if response.headers.get("finish-reason") == "CONTENT_FILTERED":
                self.logger.warning("Generation failed NSFW classifier")
                return None

            # Save the generated image
            filename, _ = os.path.splitext(os.path.basename(params.image_path))
            output_path = f"{self.output_directory}/uncrop_{filename}_{params.seed}.{params.output_format}"
            with open(output_path, "wb") as f:
                f.write(response.content)

            # Add watermark
            self._add_watermark(output_path, output_path, "logo.png")

            # Clean up temporary resized image if it exists
            if "resized_" in params.image_path:
                os.remove(params.image_path)

            self.logger.info(f"✅ Outpainted image saved as: {output_path}")
            return output_path

        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"HTTP Error in outpainting: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            self.logger.error(f"Error in uncrop_image: {e}", exc_info=True)
            return None
