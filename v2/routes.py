from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
)
from telegram.constants import ChatAction
import logging
import os
import asyncio
import time
import functools
from typing import Optional


from helper import AuthHelper, ImageHelper
from models import (
    ConversationState,
    ImageConfig,
    GenerationParams,
    ReimagineParams,
    UnCropParams,
)


# Centralized error handling decorator
def handle_errors(func):
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(self, update, context, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            await update.effective_message.reply_text("❌ An error occurred. Please try again later.")
            return ConversationHandler.END
    return wrapper


# Decorator to enforce correct conversation state
def validate_state(expected_state: ConversationState):
    """No-op decorator for conversation state validation."""
    def decorator(func):
        return func
    return decorator


class TelegramRoutes:
    def __init__(self, auth_helper, image_helper):
        self.auth_helper = auth_helper
        self.image_helper = image_helper
        self.logger = logging.getLogger(__name__)

    async def _update_last_message_time(self, context: ContextTypes.DEFAULT_TYPE):
        """Updates the last message time in user_data."""
        context.user_data["last_message_time"] = time.time()

    @handle_errors
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text("🔒 Sorry, you are not authorized to use this bot.")
            return
        welcome_message = (
            f"🌟 Welcome, {update.effective_user.first_name}!\n\n"
            "I'm your AI-powered image assistant. Here's what I can do for you:\n\n"
            "🎨 *Generate Images*: Use /imagine to create AI-generated artwork from text prompts.\n"
            "🖼️ *Imagine V2*: Use /imagine_v2 to generate images with new image generation model.\n"
            "🔄 *Reimagine Images*: Use /reimagine to transform an existing image based on a new concept.\n"
            "📈 *Upscale Images*: Use /upscale to enhance image quality and resolution.\n"
            "🖼️ *Uncrop/Outpaint*: Use /uncrop to expand images beyond their original borders.\n\n"
            "🚀 *How to Use Me:*\n"
            "1️⃣ Choose a command (/imagine, /imaginev2, /reimagine, /upscale, or /uncrop).\n"
            "2️⃣ Follow the steps to provide the necessary details.\n"
            "3️⃣ Wait for me to generate your result!\n\n"
            "Use /help for more details about each feature."
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    @handle_errors
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text("🔒 Sorry, you are not authorized to use this bot.")
            return
        help_text = (
            "🤖 *AI Image Assistant - Commands Guide*\n\n"
            "🎨 */imagine* - Generate a new AI image from a text description.\n"
            "🖼️ */imaginev2* - Generate images with new image generation model.\n"
            "🔄 */reimagine* - Modify an existing image based on a new concept.\n"
            "📈 */upscale* - Enhance the resolution and quality of an image.\n"
            "🖼️ */uncrop* - Expand images beyond their original borders (outpainting).\n"
            "⚙️ */set_watermark* - Toggle watermarking (Admins only).\n"
            "❌ */cancel* - Cancel the current operation.\n\n"
            "✨ *Tips for Best Results:*\n"
            "• Be detailed in your prompts for more accurate results.\n"
            "• For /uncrop, choose aspect ratios that make sense for your image.\n"
            "• Try different styles and sizes for better results.\n"
            "• Use simple, clear descriptions for best uncrop/outpaint results.\n\n"
            "Need help? Just start a command and follow the instructions! 🚀"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    @handle_errors
    async def set_watermark_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        user_id = str(update.message.from_user.id)
        if not self.auth_helper.is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to change this setting.")
            return
        status = "ON ✅" if self.image_helper.watermark_enabled else "OFF ❌"
        keyboard = [
            [
                InlineKeyboardButton("Enable ✅", callback_data="set_watermark_on"),
                InlineKeyboardButton("Disable ❌", callback_data="set_watermark_off"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"⚙️ *Watermark Status:* {status}\n\n"
            "🔽 Choose an option below to update:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    @handle_errors
    async def watermark_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        query = update.callback_query
        await query.answer()
        if not self.auth_helper.is_admin(str(query.from_user.id)):
            await query.edit_message_text("❌ You are not authorized to change this setting.")
            return
        if query.data == "set_watermark_on":
            self.image_helper.set_watermark_status(True)
            new_status = "ON ✅"
        else:
            self.image_helper.set_watermark_status(False)
            new_status = "OFF ❌"
        await query.edit_message_text(f"⚙️ *Watermark Status Updated:* {new_status}", parse_mode="Markdown")

    @handle_errors
    async def image_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        context.user_data["current_state"] = ConversationState.WAITING_FOR_PROMPT  # Track the current state
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "🎨 Please provide a detailed prompt for your image.\n"
            "Type /cancel to cancel the operation."
        )
        return ConversationState.WAITING_FOR_PROMPT

    @validate_state(ConversationState.WAITING_FOR_PROMPT)
    @handle_errors
    async def handle_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        context.user_data["prompt"] = update.message.text
        context.user_data["current_state"] = ConversationState.WAITING_FOR_CONTROL_TYPE  # Track the current state

        # Ask user whether they want Regular or Control-Based generation
        inline_keyboard = [
            [InlineKeyboardButton(option, callback_data=option) for option in row]
            for row in [["Regular", "Control-Based"]]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.message.reply_text(
            "🖼️ Choose the generation type:", reply_markup=reply_markup
        )

        return ConversationState.WAITING_FOR_CONTROL_TYPE

    @validate_state(ConversationState.WAITING_FOR_CONTROL_TYPE)
    @handle_errors
    async def handle_control_type(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        choice = update.callback_query.data
        context.user_data["generation_type"] = choice
        context.user_data["current_state"] = ConversationState.WAITING_FOR_SIZE  # Track the current state

        if choice == "Control-Based":
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("📤 Please upload the reference image.")
            return ConversationState.WAITING_FOR_IMAGE
        else:
            # Proceed with normal image size selection
            image_config = ImageConfig()
            inline_keyboard = [
                [InlineKeyboardButton(option, callback_data=option) for option in row]
                for row in image_config.SIZE_PRESETS
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "📐 Select image size:", reply_markup=reply_markup
            )
            return ConversationState.WAITING_FOR_SIZE

    @validate_state(ConversationState.WAITING_FOR_SIZE)
    @handle_errors
    async def handle_size(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        context.user_data["size"] = update.callback_query.data
        context.user_data["current_state"] = ConversationState.WAITING_FOR_STYLE  # Track the current state

        # Instantiate ImageConfig
        image_config = ImageConfig()
        inline_keyboard = [
            [InlineKeyboardButton(option, callback_data=option) for option in row]
            for row in image_config.STYLE_PRESETS
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("🎭 Select image style:", reply_markup=reply_markup)
        return ConversationState.WAITING_FOR_STYLE

    @validate_state(ConversationState.WAITING_FOR_STYLE)
    @handle_errors
    async def handle_style(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles style selection; schedules background image processing."""
        style = update.callback_query.data
        context.user_data["style"] = style
        generation_type = context.user_data.get("generation_type")
        context.user_data.pop("current_state", None)
        # Acknowledge button and update UI
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("🎨 Generating your image...")
        # Prepare data for background task
        prompt = context.user_data.get("prompt", "")
        size = context.user_data.get("size", "square")
        control_image = context.user_data.get("control_image", None)
        chat_id = update.effective_chat.id
        bot = context.bot
        # Launch background processing
        asyncio.create_task(
            self._process_image(
                bot, chat_id, generation_type, style, prompt, size, control_image
            )
        )
        return ConversationHandler.END

    async def _process_image(
        self,
        bot,
        chat_id: int,
        generation_type: str,
        style: str,
        prompt: str,
        size: str,
        control_image: Optional[str],
    ):
        try:
            await bot.send_chat_action(
                chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO
            )
            if generation_type == "Reimagine":
                params = ReimagineParams(
                    prompt=prompt, control_image=control_image, style=style
                )
                send_func = bot.send_photo
                caption = "🎭 Here's your reimagined image!"
            else:
                params = GenerationParams(
                    prompt=prompt, style=style, size=size, control_image=control_image
                )
                send_func = bot.send_photo
                caption = "🎨 Here's your generated image!"
            image_path = (
                self.image_helper.reimagine_image(params)
                if generation_type == "Reimagine"
                else self.image_helper.generate_image(params)
            )
            if not image_path:
                raise Exception("Image processing failed")
            with open(image_path, "rb") as f:
                await send_func(chat_id=chat_id, photo=f, caption=caption)
            os.remove(image_path)
        except Exception as e:
            self.logger.error(f"Error in background image processing: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Sorry, there was an error processing your image. Please try again.",
            )

    @handle_errors
    async def upscale_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles /upscale command and asks user to select the upscaling method."""
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return ConversationHandler.END

        # Set generation_type to "Upscale"
        context.user_data["generation_type"] = "Upscale"

        # Ask user to select upscaling method
        inline_keyboard = [
            [InlineKeyboardButton(option, callback_data=option) for option in row]
            for row in [["Conservative", "Creative", "Fast"]]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.message.reply_text(
            "🖼️ Choose the upscaling method (Conservative, Creative, Fast):",
            reply_markup=reply_markup,
        )

        return ConversationState.WAITING_FOR_UPSCALE_METHOD

    @handle_errors
    async def handle_upscale_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the input of the upscaling prompt."""
        context.user_data["upscale_prompt"] = update.message.text

        # If the method is "creative", ask for a style preset
        if context.user_data.get("upscale_method") == "creative":
            image_config = ImageConfig()
            inline_keyboard = [
                [InlineKeyboardButton(option, callback_data=option) for option in row]
                for row in image_config.STYLE_PRESETS
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            await update.message.reply_text(
                "🎭 Select a style preset for creative upscaling:",
                reply_markup=reply_markup,
            )
            return ConversationState.WAITING_FOR_STYLE
        else:
            # For "conservative" mode, proceed to ask for the image
            await update.message.reply_text(
                "📷 Please send the image you want to upscale."
            )
            return ConversationState.WAITING_FOR_IMAGE

    @handle_errors
    async def handle_upscale_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the selection of upscaling method (conservative, creative, fast)."""
        method = update.callback_query.data
        if method not in ["conservative", "creative", "fast"]:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "❌ Invalid method. Please choose 'Conservative', 'Creative', or 'Fast'."
            )
            return ConversationState.WAITING_FOR_UPSCALE_METHOD

        context.user_data["upscale_method"] = method

        if method in ["conservative", "creative"]:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("✏️ Please provide a prompt for upscaling.")
            return ConversationState.WAITING_FOR_UPSCALE_PROMPT
        else:
            # For "fast" mode, proceed to ask for the image
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "📷 Please send the image you want to upscale."
            )
            return ConversationState.WAITING_FOR_IMAGE

    @handle_errors
    async def handle_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles image upload for reimagine, upscale, and control-based generation."""
        try:
            self.logger.info("📸 User sent an image. Requesting file from Telegram...")

            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_path = f"./image/{photo.file_id}.jpg"

            self.logger.info(f"📥 Starting image download: {file_path}")
            await asyncio.wait_for(file.download_to_drive(file_path), timeout=60)

            self.logger.info(f"✅ Image successfully downloaded: {file_path}")

            # Retrieve generation_type from context
            generation_type = context.user_data.get("generation_type")

            if generation_type is None:
                self.logger.error("⚠️ Missing generation_type in context.")
                await update.message.reply_text(
                    "❌ Something went wrong. Please restart the command."
                )
                return ConversationHandler.END

            if generation_type == "Reimagine":
                context.user_data["control_image"] = file_path

                # Ask for style selection
                image_config = ImageConfig()
                inline_keyboard = [
                    [InlineKeyboardButton(option, callback_data=option) for option in row]
                    for row in image_config.STYLE_PRESETS
                ]
                reply_markup = InlineKeyboardMarkup(inline_keyboard)
                await update.message.reply_text(
                    "🎭 Select a style for reimagining:", reply_markup=reply_markup
                )
                return ConversationState.WAITING_FOR_STYLE

            elif generation_type == "Control-Based":
                context.user_data["control_image"] = file_path
                image_config = ImageConfig()
                inline_keyboard = [
                    [InlineKeyboardButton(option, callback_data=option) for option in row]
                    for row in image_config.SIZE_PRESETS
                ]
                reply_markup = InlineKeyboardMarkup(inline_keyboard)
                await update.message.reply_text(
                    "📐 Select image size:", reply_markup=reply_markup
                )
                return ConversationState.WAITING_FOR_SIZE

            elif generation_type == "Upscale":
                context.user_data["image"] = file_path
                inline_keyboard = [
                    [InlineKeyboardButton(option, callback_data=option) for option in row]
                    for row in [["webp", "jpeg", "png"]]
                ]
                reply_markup = InlineKeyboardMarkup(inline_keyboard)
                await update.message.reply_text(
                    "📁 Select output format:", reply_markup=reply_markup
                )
                return ConversationState.WAITING_FOR_FORMAT

            else:
                self.logger.error(f"⚠️ Unknown generation_type: {generation_type}")
                await update.message.reply_text(
                    "❌ Something went wrong. Please restart the command."
                )
                if "current_state" in context.user_data:
                    del context.user_data["current_state"]  # Clear the current state
                return ConversationHandler.END

        except asyncio.TimeoutError:
            self.logger.error("⏳ Image download timed out!")
            await update.message.reply_text(
                "❌ Image download timed out. Please try again."
            )
            return ConversationHandler.END
        except Exception as e:
            self.logger.error(f"❌ Error during image download: {e}")
            await update.message.reply_text(
                "❌ Failed to download image. Please try again."
            )
            if "current_state" in context.user_data:
                del context.user_data["current_state"]  # Clear the current state
            return ConversationHandler.END

    @handle_errors
    async def handle_format(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles image upscaling and sends back the result as a file."""
        upscale_method = context.user_data.get("upscale_method", "fast")

        if upscale_method == "creative":
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "🔄 Upscaling your image using the creative method... This may take a few moments. Please wait."
            )
        else:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "🔄 Upscaling your image..."
            )

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
            )

            image_path = context.user_data.get("image", "")
            output_format = update.callback_query.data
            prompt = context.user_data.get("upscale_prompt", "")
            negative_prompt = "2 faces, 2 heads, bad anatomy, blurry, cloned face, cropped image, cut-off, deformed hands, disconnected limbs, disgusting, disfigured, draft, duplicate artifact, extra fingers, extra limb, floating limbs, gloss proportions, grain, gross proportions, long body, long neck, low-res, mangled, malformed, malformed hands, missing arms, missing limb, morbid, mutation, mutated, mutated hands, mutilated, mutilated hands, multiple heads, negative aspect, out of frame, poorly drawn, poorly drawn face, poorly drawn hands, signatures, surreal, tiling, twisted fingers, ugly"
            creativity = 0.35  # Default creativity value
            style_preset = (
                context.user_data.get("style", "None")
                if upscale_method == "creative"
                else "None"
            )

            upscaled_image_path = self.image_helper.upscale_image(
                image_path,
                output_format,
                method=upscale_method,
                prompt=prompt,
                negative_prompt=negative_prompt,
                creativity=creativity,
                style_preset=style_preset,
            )

            if not upscaled_image_path:
                raise Exception("Image upscaling failed")

            with open(upscaled_image_path, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=f"upscaled.{output_format}",  # ✅ Ensures correct filename when sending
                    caption=f"🖼️ Here's your upscaled image (using {upscale_method} method).",
                )

            os.remove(upscaled_image_path)

        except Exception as e:
            self.logger.error(f"Error in handle_format: {e}")
            await update.effective_message.reply_text(
                "❌ Sorry, there was an error upscaling your image. Please try again."
            )
            if "current_state" in context.user_data:
                del context.user_data["current_state"]  # Clear the current state

        return ConversationHandler.END

    @handle_errors
    async def cancel_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        await update.message.reply_text(
            "Operation cancelled."
        )
        context.user_data.clear()  # Reset all session data
        return ConversationHandler.END

    @handle_errors
    async def reimagine_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the /reimagine command."""
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return ConversationHandler.END

        # Set generation_type to "Reimagine"
        context.user_data["generation_type"] = "Reimagine"

        # Ask user to select method (Image or Sketch)
        inline_keyboard = [
            [InlineKeyboardButton(option, callback_data=option) for option in row]
            for row in [["Image", "Sketch"]]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        await update.message.reply_text(
            "🖼️ Choose the method (Image or Sketch):", reply_markup=reply_markup
        )

        return ConversationState.WAITING_FOR_METHOD

    @handle_errors
    async def handle_reimagine_style(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Stores the selected style and asks for a reimagine description."""
        context.user_data["style"] = update.callback_query.data
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("✏️ Now provide a description for reimagining.")
        return ConversationState.WAITING_FOR_PROMPT

    @handle_errors
    async def handle_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the selection of method (Image or Sketch)."""
        method = update.callback_query.data.lower()
        if method not in ["image", "sketch"]:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "❌ Invalid method. Please choose 'Image' or 'Sketch'."
            )
            return ConversationState.WAITING_FOR_METHOD

        context.user_data["method"] = method
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("📤 Please upload the image or sketch.")
        return ConversationState.WAITING_FOR_IMAGE

    @handle_errors
    async def handle_reimagine_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles reimagine prompt input and starts image transformation."""
        await update.message.reply_text(
            "✨ Reimagining your image..."
        )

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )

            params = ReimagineParams(
                prompt=update.message.text,
                control_image=context.user_data["control_image"],
                style=context.user_data.get("style", "None"),
                method=context.user_data.get(
                    "method", "image"
                ),  # Include the selected method
            )

            image_path = self.image_helper.reimagine_image(params)

            if not image_path:
                raise Exception("Reimagining failed")

            with open(image_path, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption="🎭 Here's your reimagined image!",
                )

            os.remove(image_path)

        except Exception as e:
            self.logger.error(f"Error in handle_reimagine_prompt: {e}")
            await update.effective_message.reply_text(
                "❌ Sorry, there was an error reimagining your image. Please try again."
            )
            if "current_state" in context.user_data:
                del context.user_data["current_state"]  # Clear the current state

        return ConversationHandler.END

    @handle_errors
    async def imagine_v2_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the /imagine_v2 command to start the new image generation flow."""
        if not self.auth_helper.is_admin(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "🎨 Please provide a detailed prompt for your image.\n"
            "Type /cancel to cancel the operation."
        )
        return ConversationState.WAITING_FOR_PROMPT_V2

    @handle_errors
    async def handle_prompt_v2(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the prompt input for the new image generation flow."""
        context.user_data["prompt"] = update.message.text

        # Provide a keyboard with predefined aspect ratio options
        aspect_ratio_keyboard = [
            ["16:9", "1:1", "4:5"],
            ["9:16", "3:2", "2:3"],
            ["21:9", "5:4", "9:21"],
        ]
        inline_keyboard = [
            [InlineKeyboardButton(option, callback_data=option) for option in row]
            for row in aspect_ratio_keyboard
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        await update.message.reply_text(
            "📐 Please select an aspect ratio from the options below:",
            reply_markup=reply_markup,
        )
        return ConversationState.WAITING_FOR_ASPECT_RATIO_V2

    @handle_errors
    async def handle_aspect_ratio_v2(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the aspect ratio input for the new image generation flow."""
        aspect_ratio = update.callback_query.data
        context.user_data["aspect_ratio"] = aspect_ratio

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "📤 (Optional) Upload an image to use as the starting point, or type /skip to continue without one."
        )
        return ConversationState.WAITING_FOR_IMAGE_V2

    @handle_errors
    async def handle_image_v2(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the optional image upload for the new image generation flow."""
        if update.message.text == "/skip":
            context.user_data["image"] = None
        else:
            try:
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                file_path = f"./image/{photo.file_id}.jpg"
                await asyncio.wait_for(file.download_to_drive(file_path), timeout=60)
                context.user_data["image"] = file_path
            except asyncio.TimeoutError:
                await update.message.reply_text(
                    "❌ Image download timed out. Please try again."
                )
                return ConversationHandler.END
            except Exception as e:
                self.logger.error(f"Error during image download: {e}")
                await update.message.reply_text(
                    "❌ Failed to download image. Please try again."
                )
                return ConversationHandler.END

        await update.message.reply_text(
            "🖼️ Generating your image..."
        )

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )

            image_path = self.image_helper.generate_image_v2(
                prompt=context.user_data["prompt"],
                output_format="png",
                image=context.user_data.get("image"),
                aspect_ratio=context.user_data.get("aspect_ratio"),
            )

            if not image_path:
                raise Exception("Image generation failed")

            with open(image_path, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption="🎨 Here's your generated image!",
                )

            os.remove(image_path)

        except Exception as e:
            self.logger.error(f"Error in handle_image_v2: {e}")
            await update.effective_message.reply_text(
                "❌ Sorry, there was an error generating your image. Please try again."
            )

        return ConversationHandler.END

    @handle_errors
    async def uncrop_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the /uncrop command to start the outpainting process."""
        if not self.auth_helper.is_admin(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "🖼️ Please upload the image you want to uncrop (outpaint).\n"
            "Type /cancel to cancel the operation."
        )
        return ConversationState.WAITING_FOR_UNCROP_IMAGE

    @handle_errors
    async def handle_uncrop_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the image upload for uncrop/outpaint."""
        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_path = f"./image/{photo.file_id}_uncrop.jpg"
            await asyncio.wait_for(file.download_to_drive(file_path), timeout=60)

            context.user_data["uncrop_image"] = file_path

            # Provide aspect ratio options
            aspect_ratio_keyboard = [
                ["16:9", "1:1", "4:5"],
                ["9:16", "3:2", "2:3"],
                ["21:9", "5:4", "9:21"],
            ]
            inline_keyboard = [
                [InlineKeyboardButton(option, callback_data=option) for option in row]
                for row in aspect_ratio_keyboard
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)

            await update.message.reply_text(
                "📐 What aspect ratio would you like for the outpainted image?",
                reply_markup=reply_markup,
            )
            return ConversationState.WAITING_FOR_UNCROP_ASPECT_RATIO
        except Exception as e:
            self.logger.error(f"Error in handle_uncrop_image: {e}")
            await update.message.reply_text(
                "❌ Failed to process image. Please try again."
            )
            return ConversationHandler.END

    @handle_errors
    async def handle_uncrop_aspect_ratio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the aspect ratio selection for uncrop/outpaint."""
        aspect_ratio = update.callback_query.data
        if ":" not in aspect_ratio or len(aspect_ratio.split(":")) != 2:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "❌ Invalid aspect ratio format. Please use format like '16:9' or select from the options."
            )
            return ConversationState.WAITING_FOR_UNCROP_ASPECT_RATIO

        context.user_data["uncrop_aspect_ratio"] = aspect_ratio

        # Add position selection keyboard with skip option
        position_keyboard = [
            ["Top Left", "Top", "Top Right"],
            ["Left", "Auto/Original", "Right"],
            ["Bottom Left", "Bottom", "Bottom Right"],
            ["Skip (Use Auto)"],
        ]
        inline_keyboard = [
            [InlineKeyboardButton(option, callback_data=option) for option in row]
            for row in position_keyboard
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "📍 Select where to position the original image in the outpainted result (or skip to use auto positioning):",
            reply_markup=reply_markup,
        )
        return ConversationState.WAITING_FOR_UNCROP_POSITION

    @handle_errors
    async def handle_uncrop_position(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the position selection for uncrop/outpaint."""
        position = update.callback_query.data.lower().replace(" ", "_")

        # Handle skip option
        if position in ["skip", "skip_(use_auto)"]:
            context.user_data["uncrop_position"] = "auto"
        else:
            valid_positions = [
                "top_left",
                "top",
                "top_right",
                "left",
                "auto/original",
                "right",
                "bottom_left",
                "bottom",
                "bottom_right",
            ]

            if position not in valid_positions:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    "❌ Invalid position. Please select from the options."
                )
                return ConversationState.WAITING_FOR_UNCROP_POSITION

            # Special case for "Auto/Original" selection
            if position == "auto/original":
                context.user_data["uncrop_position"] = "auto"
            else:
                context.user_data["uncrop_position"] = position

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "✏️ (Optional) Provide a prompt to guide the outpainting, or type /skip:"
        )
        return ConversationState.WAITING_FOR_UNCROP_PROMPT

    @handle_errors
    async def handle_uncrop_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles the uncrop prompt and starts the outpainting process."""
        if update.message.text != "/skip":
            context.user_data["uncrop_prompt"] = update.message.text

        await update.message.reply_text(
            "🔄 Performing outpainting (uncrop)... This may take a moment.\n"
            "⚠️ Note: Large images will be automatically resized to fit API limits."
        )

        try:
            params = UnCropParams(
                image_path=context.user_data["uncrop_image"],
                target_aspect_ratio=context.user_data["uncrop_aspect_ratio"],
                prompt=context.user_data.get("uncrop_prompt", ""),
                output_format="png",
                position=context.user_data.get("uncrop_position", "middle"),
            )

            image_path = self.image_helper.uncrop_image(params)

            if not image_path:
                raise Exception("Outpainting failed")

            with open(image_path, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption="🖼️ Here's your outpainted (uncropped) image!",
                )

            os.remove(image_path)

        except Exception as e:
            self.logger.error(f"Error in handle_uncrop_prompt: {e}")
            await update.effective_message.reply_text(
                "❌ Sorry, there was an error during outpainting. Please try again with a smaller image."
            )

        return ConversationHandler.END
