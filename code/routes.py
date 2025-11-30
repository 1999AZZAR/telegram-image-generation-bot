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
from typing import Optional, Any, Callable, Awaitable
import requests


from helper import AuthHelper, ImageHelper
from models import (
    ConversationState,
    ImageConfig,
    GenerationParams,
    ReimagineParams,
    UnCropParams,
)


# Centralized error handling decorator
def handle_errors(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    @functools.wraps(func)
    async def wrapper(self: Any, update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        try:
            return await func(self, update, context, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            await update.effective_message.reply_text("An error occurred. Please try again later.")
            context.user_data.clear()
            return ConversationHandler.END
    return wrapper


# Decorator to enforce correct conversation state
def validate_state(expected_state: ConversationState) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """No-op decorator for conversation state validation."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func
    return decorator


class TelegramRoutes:
    def __init__(self, auth_helper: AuthHelper, image_helper: ImageHelper) -> None:
        self.auth_helper = auth_helper
        self.image_helper = image_helper
        self.logger = logging.getLogger(__name__)

    async def _update_last_message_time(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Updates the last message time in user_data."""
        context.user_data["last_message_time"] = time.time()

    @handle_errors
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text("Access denied. You are not authorized to use this bot.")
            return
        welcome_message = (
            f"Welcome, {update.effective_user.first_name}!\n\n"
            "I am an AI-powered image generation assistant. Here are the available features:\n\n"
            "*Generate Images*: Use /imagine to create AI-generated artwork from text descriptions.\n"
            "*Imagine V2*: Use /imaginev2 to generate images with the enhanced generation model.\n"
            "*Reimagine Images*: Use /reimagine to transform existing images with new concepts.\n"
            "*Upscale Images*: Use /upscale to enhance image resolution and quality.\n"
            "*Uncrop/Outpaint*: Use /uncrop to expand images beyond their original boundaries.\n\n"
            "*Getting Started:*\n"
            "1. Choose a command (/imagine, /imaginev2, /reimagine, /upscale, or /uncrop).\n"
            "2. Follow the prompts to provide the required information.\n"
            "3. Wait for the system to process and deliver your result.\n\n"
            "Use /help for detailed information about each feature."
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    @handle_errors
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text("Access denied. You are not authorized to use this bot.")
            return
        help_text = (
            "*AI Image Generation Bot - Command Reference*\n\n"
            "*Image Generation:*\n"
            "*/imagine* - Generate new images from text descriptions.\n"
            "*/imaginev2* - Generate images using the enhanced model.\n"
            "*/reimagine* - Transform existing images with new concepts.\n\n"
            "*Image Editing:*\n"
            "*/erase* - Remove objects from images using masks.\n"
            "*/search_replace* - Find and replace objects in images.\n"
            "*/inpaint* - Fill in masked areas with generated content.\n\n"
            "*Image Enhancement:*\n"
            "*/upscale* - Enhance image resolution and quality.\n"
            "*/uncrop* - Expand images beyond their original boundaries.\n\n"
            "*Administration:*\n"
            "*/set_watermark* - Toggle watermark application (administrators only).\n"
            "*/cancel* - Cancel the current operation.\n\n"
            "*Optimization Tips:*\n"
            "• Provide detailed prompts for more accurate results.\n"
            "• Select appropriate aspect ratios for your use case.\n"
            "• Experiment with different styles to achieve desired results.\n"
            "• Use clear, specific descriptions for best editing results.\n"
            "• Create accurate masks for erase and inpaint operations.\n\n"
            "Start any command and follow the interactive prompts for guidance."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    @handle_errors
    async def set_watermark_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        user_id = str(update.message.from_user.id)
        if not self.auth_helper.is_admin(user_id):
            await update.message.reply_text("Access denied. You are not authorized to modify this setting.")
            return
        status = "Enabled" if self.image_helper.watermark_enabled else "Disabled"
        keyboard = [
            [
                InlineKeyboardButton("Enable", callback_data="set_watermark_on"),
                InlineKeyboardButton("Disable", callback_data="set_watermark_off"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"*Watermark Status:* {status}\n\n"
            "Select an option below to modify the setting:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    @handle_errors
    async def watermark_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._update_last_message_time(context)
        query = update.callback_query
        await query.answer()
        if not self.auth_helper.is_admin(str(query.from_user.id)):
            await query.edit_message_text("Access denied. You are not authorized to modify this setting.")
            return
        if query.data == "set_watermark_on":
            self.image_helper.set_watermark_status(True)
            new_status = "Enabled"
        else:
            self.image_helper.set_watermark_status(False)
            new_status = "Disabled"
        await query.edit_message_text(f"*Watermark Status Updated:* {new_status}", parse_mode="Markdown")

    @handle_errors
    async def image_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        context.user_data["current_state"] = ConversationState.WAITING_FOR_PROMPT  # Track the current state
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "Access denied. You are not authorized to use this bot."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Please provide a detailed description for your image.\n"
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
            "Select the generation method:", reply_markup=reply_markup
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
            await update.callback_query.edit_message_text("Please upload the reference image.")
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
                "Select image dimensions:", reply_markup=reply_markup
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
        await update.callback_query.edit_message_text("Select artistic style:", reply_markup=reply_markup)
        return ConversationState.WAITING_FOR_STYLE

    @validate_state(ConversationState.WAITING_FOR_STYLE)
    @handle_errors
    async def handle_style(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        style = update.callback_query.data
        context.user_data["style"] = style
        generation_type = context.user_data.get("generation_type")
        context.user_data.pop("current_state", None)
        await update.callback_query.answer()
        if generation_type == "Upscale" and context.user_data.get("upscale_method") == "creative":
            await update.callback_query.edit_message_text(
                "Please upload the image you want to enhance."
            )
            return ConversationState.WAITING_FOR_IMAGE
        await update.callback_query.edit_message_text("Generating your image...")
        prompt = context.user_data.get("prompt", "")
        size = context.user_data.get("size", "square")
        control_image = context.user_data.get("control_image", None)
        chat_id = update.effective_chat.id
        bot = context.bot
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        asyncio.create_task(
            self._process_image(
                bot, chat_id, generation_type, style, prompt, size, control_image
            )
        )
        return ConversationHandler.END

    async def _process_image(
        self,
        bot: Any,
        chat_id: int,
        generation_type: str,
        style: str,
        prompt: str,
        size: str,
        control_image: Optional[str],
    ) -> None:
        try:
            await bot.send_chat_action(
                chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO
            )
            # Progress update: after 10 seconds, send a message if still running
            import asyncio
            progress_task = asyncio.create_task(self._send_progress_update(bot, chat_id))
            if generation_type == "Reimagine":
                params = ReimagineParams(
                    prompt=prompt, control_image=control_image, style=style
                )
                send_func = bot.send_photo
                caption = "Here is your reimagined image."
                image_path = await asyncio.to_thread(self.image_helper.reimagine_image, params)
            else:
                params = GenerationParams(
                    prompt=prompt, style=style, size=size, control_image=control_image
                )
                send_func = bot.send_photo
                caption = "Here is your generated image."
                image_path = await asyncio.to_thread(self.image_helper.generate_image, params)
            progress_task.cancel()
            if not image_path:
                raise Exception("Image processing failed")
            from io import BytesIO
            file_bytes = await asyncio.to_thread(lambda: open(image_path, "rb").read())
            file_obj = BytesIO(file_bytes)
            await send_func(chat_id=chat_id, photo=file_obj, caption=caption)
            await asyncio.to_thread(os.remove, image_path)
        except Exception as e:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            self.logger.error(f"Error in background image processing: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text="An error occurred while processing your image. Please try again later. If the problem persists, contact support.",
            )

    async def _send_progress_update(self, bot: Any, chat_id: int) -> None:
        await asyncio.sleep(10)
        await bot.send_message(chat_id=chat_id, text="Processing is still in progress. Please wait.")

    @handle_errors
    async def upscale_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles /upscale command and asks user to select the upscaling method."""
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "Access denied. You are not authorized to use this bot."
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
            "Select the enhancement method (Conservative, Creative, Fast):",
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
                "Select a style for creative enhancement:",
                reply_markup=reply_markup,
            )
            return ConversationState.WAITING_FOR_STYLE
        else:
            # For "conservative" mode, proceed to ask for the image
            await update.message.reply_text(
                "Please upload the image you want to enhance."
            )
            return ConversationState.WAITING_FOR_IMAGE

    @handle_errors
    async def handle_upscale_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the selection of upscaling method (conservative, creative, fast)."""
        method = update.callback_query.data.strip().lower()
        valid_methods = {"conservative", "creative", "fast"}
        if method not in valid_methods:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "Invalid method selected. Please choose 'Conservative', 'Creative', or 'Fast'."
            )
            context.user_data.clear()
            return ConversationHandler.END

        context.user_data["upscale_method"] = method

        if method in {"conservative", "creative"}:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("Please provide a description for the enhancement.")
            return ConversationState.WAITING_FOR_UPSCALE_PROMPT
        else:
            # For "fast" mode, proceed to ask for the image
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "Please upload the image you want to enhance."
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
                self.logger.error("Missing generation_type in context.")
                await update.message.reply_text(
                    "An error occurred. Please restart the command."
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
                    "Select a style for transformation:", reply_markup=reply_markup
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
                    "Select image dimensions:", reply_markup=reply_markup
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
                self.logger.error(f"Unknown generation_type: {generation_type}")
                await update.message.reply_text(
                    "An error occurred. Please restart the command."
                )
                if "current_state" in context.user_data:
                    del context.user_data["current_state"]  # Clear the current state
                return ConversationHandler.END

        except asyncio.TimeoutError:
            self.logger.error("Image download timed out!")
            await update.message.reply_text(
                "Image download timed out. Please try again."
            )
            return ConversationHandler.END
        except Exception as e:
            self.logger.error(f"Error during image download: {e}")
            await update.message.reply_text(
                "Failed to download image. Please try again."
            )
            if "current_state" in context.user_data:
                del context.user_data["current_state"]  # Clear the current state
            return ConversationHandler.END

    @handle_errors
    async def handle_format(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        upscale_method = context.user_data.get("upscale_method", "fast")
        if upscale_method == "creative":
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "Enhancing your image using the creative method... This may take a few moments. Please wait."
            )
        else:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "Enhancing your image..."
            )
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
            )
            import asyncio
            progress_task = asyncio.create_task(self._send_progress_update(context.bot, update.effective_chat.id))
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
            upscaled_image_path = await asyncio.to_thread(
                self.image_helper.upscale_image,
                image_path,
                output_format,
                upscale_method,
                prompt,
                negative_prompt,
                creativity,
                style_preset,
            )
            progress_task.cancel()
            if not upscaled_image_path:
                raise Exception("Image upscaling failed")
            from io import BytesIO
            file_bytes = await asyncio.to_thread(lambda: open(upscaled_image_path, "rb").read())
            file_obj = BytesIO(file_bytes)
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_obj,
                filename=f"upscaled.{output_format}",
                caption=f"Here is your enhanced image (using {upscale_method} method).",
            )
            await asyncio.to_thread(os.remove, upscaled_image_path)
        except requests.exceptions.Timeout:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            self.logger.error("Upscaling timed out after multiple attempts.")
            await update.effective_message.reply_text(
                "The enhancement operation timed out. This can happen if the server is busy or the image is too large. Please try again later or use a smaller image."
            )
            context.user_data.clear()
            return ConversationHandler.END
        except Exception as e:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            self.logger.error(f"Error in handle_format: {e}")
            await update.effective_message.reply_text(
                "An error occurred while enhancing your image. Please try again later. If the problem persists, contact support."
            )
            context.user_data.clear()
            return ConversationHandler.END
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
                "Access denied. You are not authorized to use this bot."
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
            "Select the transformation method (Image or Sketch):", reply_markup=reply_markup
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
        await update.callback_query.edit_message_text("Please provide a description for the transformation.")
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
                "Invalid method selected. Please choose 'Image' or 'Sketch'."
            )
            return ConversationState.WAITING_FOR_METHOD

        context.user_data["method"] = method
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Please upload the image or sketch.")
        return ConversationState.WAITING_FOR_IMAGE

    @handle_errors
    async def handle_reimagine_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles reimagine prompt input and starts image transformation."""
        await update.message.reply_text(
            "Transforming your image..."
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

            image_path = await asyncio.to_thread(self.image_helper.reimagine_image, params)

            if not image_path:
                raise Exception("Reimagining failed")

            with open(image_path, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo,
                    caption="Here is your transformed image.",
                )

            await asyncio.to_thread(os.remove, image_path)

        except Exception as e:
            self.logger.error(f"Error in handle_reimagine_prompt: {e}")
            await update.effective_message.reply_text(
                "An error occurred while transforming your image. Please try again."
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
                "Access denied. You are not authorized to use this bot."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Please provide a detailed description for your image.\n"
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
            "Please select an aspect ratio from the options below:",
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
            "(Optional) Upload an image to use as the starting point, or type /skip to continue without one."
        )
        return ConversationState.WAITING_FOR_IMAGE_V2

    @handle_errors
    async def handle_image_v2(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
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
                    "Image download timed out. Please try again."
                )
                return ConversationHandler.END
            except Exception as e:
                self.logger.error(f"Error during image download: {e}")
                await update.message.reply_text(
                    "Failed to download image. Please try again."
                )
                return ConversationHandler.END
        await update.message.reply_text(
            "Generating your image..."
        )
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )
            # Progress update: after 10 seconds, send a message if still running
            import asyncio
            progress_task = asyncio.create_task(self._send_progress_update(context.bot, update.effective_chat.id))
            image_path = await asyncio.to_thread(
                self.image_helper.generate_image_v2,
                context.user_data["prompt"],
                "png",
                context.user_data.get("image"),
                None,
                context.user_data.get("aspect_ratio"),
            )
            progress_task.cancel()
            if not image_path:
                raise Exception("Image generation failed")
            from io import BytesIO
            file_bytes = await asyncio.to_thread(lambda: open(image_path, "rb").read())
            file_obj = BytesIO(file_bytes)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_obj,
                caption="Here is your generated image.",
            )
            await asyncio.to_thread(os.remove, image_path)
        except Exception as e:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            self.logger.error(f"Error in handle_image_v2: {e}")
            await update.effective_message.reply_text(
                "An error occurred while generating your image. Please try again later. If the problem persists, contact support."
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
                "Access denied. You are not authorized to use this bot."
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Please upload the image you want to expand (outpaint).\n"
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
                "Select the aspect ratio for the expanded image:",
                reply_markup=reply_markup,
            )
            return ConversationState.WAITING_FOR_UNCROP_ASPECT_RATIO
        except Exception as e:
            self.logger.error(f"Error in handle_uncrop_image: {e}")
            await update.message.reply_text(
                "Failed to process image. Please try again."
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
                "Invalid aspect ratio format. Please use format like '16:9' or select from the options."
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
            "Select where to position the original image in the expanded result (or skip to use automatic positioning):",
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
                    "Invalid position selected. Please choose from the available options."
                )
                return ConversationState.WAITING_FOR_UNCROP_POSITION

            # Special case for "Auto/Original" selection
            if position == "auto/original":
                context.user_data["uncrop_position"] = "auto"
            else:
                context.user_data["uncrop_position"] = position

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "(Optional) Provide a description to guide the expansion, or type /skip:"
        )
        return ConversationState.WAITING_FOR_UNCROP_PROMPT

    @handle_errors
    async def handle_uncrop_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        if update.message.text != "/skip":
            context.user_data["uncrop_prompt"] = update.message.text
        await update.message.reply_text(
            "Expanding image boundaries... This may take a moment.\n"
            "Note: Large images will be automatically resized to meet API requirements."
        )
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )
            # Progress update: after 10 seconds, send a message if still running
            import asyncio
            progress_task = asyncio.create_task(self._send_progress_update(context.bot, update.effective_chat.id))
            params = UnCropParams(
                image_path=context.user_data["uncrop_image"],
                target_aspect_ratio=context.user_data["uncrop_aspect_ratio"],
                prompt=context.user_data.get("uncrop_prompt", ""),
                output_format="png",
                position=context.user_data.get("uncrop_position", "middle"),
            )
            image_path = await asyncio.to_thread(self.image_helper.uncrop_image, params)
            progress_task.cancel()
            if not image_path:
                raise Exception("Outpainting failed")
            from io import BytesIO
            file_bytes = await asyncio.to_thread(lambda: open(image_path, "rb").read())
            file_obj = BytesIO(file_bytes)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_obj,
                caption="Here is your expanded image.",
            )
            await asyncio.to_thread(os.remove, image_path)
        except Exception as e:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            self.logger.error(f"Error in handle_uncrop_prompt: {e}")
            await update.effective_message.reply_text(
                "An error occurred during image expansion. Please try again later. If the problem persists, contact support."
            )
        return ConversationHandler.END

    # ==================== EDIT COMMANDS ====================

    @handle_errors
    async def erase_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Start the erase command conversation."""
        await self._update_last_message_time(context)
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text("Access denied. You are not authorized to use this bot.")
            return ConversationHandler.END

        await update.message.reply_text(
            "*Erase Objects*\n\n"
            "Send me an image that contains objects you want to erase. "
            "Then send a mask image showing which areas to remove.\n\n"
            "The mask should be a black and white image where:\n"
            "• White areas = objects to erase\n"
            "• Black areas = areas to keep\n\n"
            "Send the image or type /cancel to abort.",
            parse_mode="Markdown"
        )
        return ConversationState.WAITING_FOR_ERASE_IMAGE

    @handle_errors
    async def handle_erase_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the image input for erase command."""
        await self._update_last_message_time(context)

        if update.message.text == "/skip":
            context.user_data["erase_image"] = None
        else:
            try:
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                file_path = f"./image/{photo.file_id}_erase.jpg"
                await asyncio.wait_for(file.download_to_drive(file_path), timeout=60)
                context.user_data["erase_image"] = file_path
            except asyncio.TimeoutError:
                await update.message.reply_text("Image download timed out. Please try again.")
                return ConversationHandler.END
            except Exception as e:
                self.logger.error(f"Error during erase image download: {e}")
                await update.message.reply_text("Failed to download image. Please try again.")
                return ConversationHandler.END

        await update.message.reply_text(
            "Now send a mask image that shows which parts of the image to erase.\n\n"
            "The mask should be the same size as your image and use:\n"
            "• White pixels = areas to erase\n"
            "• Black pixels = areas to keep\n\n"
            "Send the mask image or type /cancel to abort."
        )
        return ConversationState.WAITING_FOR_ERASE_MASK

    @handle_errors
    async def handle_erase_mask(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the mask input and perform erase operation."""
        await self._update_last_message_time(context)

        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            mask_path = f"./image/{photo.file_id}_mask.jpg"
            await asyncio.wait_for(file.download_to_drive(mask_path), timeout=60)

            await update.message.reply_text("Processing your erase request...")

            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )

            progress_task = asyncio.create_task(self._send_progress_update(context.bot, update.effective_chat.id))
            image_path = await asyncio.to_thread(
                self.image_helper.erase_object,
                context.user_data["erase_image"],
                mask_path,
                "png",
            )
            progress_task.cancel()

            if not image_path:
                raise Exception("Erase operation failed")

            from io import BytesIO
            file_bytes = await asyncio.to_thread(lambda: open(image_path, "rb").read())
            file_obj = BytesIO(file_bytes)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_obj,
                caption="Here is your edited image with objects erased.",
            )
            await asyncio.to_thread(os.remove, image_path)
            await asyncio.to_thread(os.remove, context.user_data["erase_image"])
            await asyncio.to_thread(os.remove, mask_path)

        except Exception as e:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            self.logger.error(f"Error in handle_erase_mask: {e}")
            await update.effective_message.reply_text(
                "An error occurred during object erase. Please try again later. If the problem persists, contact support."
            )
        return ConversationHandler.END

    @handle_errors
    async def search_replace_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Start the search and replace command conversation."""
        await self._update_last_message_time(context)
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text("Access denied. You are not authorized to use this bot.")
            return ConversationHandler.END

        await update.message.reply_text(
            "*Search and Replace*\n\n"
            "Send me an image, then describe what you want to search for and what to replace it with.\n\n"
            "Example:\n"
            "• Search: 'red car'\n"
            "• Replace: 'blue motorcycle'\n\n"
            "Send the image or type /cancel to abort.",
            parse_mode="Markdown"
        )
        return ConversationState.WAITING_FOR_SEARCH_REPLACE_IMAGE

    @handle_errors
    async def handle_search_replace_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the image input for search and replace command."""
        await self._update_last_message_time(context)

        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_path = f"./image/{photo.file_id}_search.jpg"
            await asyncio.wait_for(file.download_to_drive(file_path), timeout=60)
            context.user_data["search_replace_image"] = file_path
        except asyncio.TimeoutError:
            await update.message.reply_text("Image download timed out. Please try again.")
            return ConversationHandler.END
        except Exception as e:
            self.logger.error(f"Error during search-replace image download: {e}")
            await update.message.reply_text("Failed to download image. Please try again.")
            return ConversationHandler.END

        await update.message.reply_text(
            "What object or element do you want to search for in the image?\n\n"
            "Example: 'red car', 'person wearing hat', 'blue sky'\n\n"
            "Type your search description or /cancel to abort."
        )
        return ConversationState.WAITING_FOR_SEARCH_PROMPT

    @handle_errors
    async def handle_search_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the search prompt input."""
        await self._update_last_message_time(context)
        context.user_data["search_prompt"] = update.message.text

        await update.message.reply_text(
            "What do you want to replace it with?\n\n"
            "Example: 'blue motorcycle', 'person with sunglasses', 'sunny day'\n\n"
            "Type your replacement description or /cancel to abort."
        )
        return ConversationState.WAITING_FOR_REPLACE_PROMPT

    @handle_errors
    async def handle_replace_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the replace prompt and perform search and replace operation."""
        await self._update_last_message_time(context)
        context.user_data["replace_prompt"] = update.message.text

        await update.message.reply_text("Processing your search and replace request...")

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )

            progress_task = asyncio.create_task(self._send_progress_update(context.bot, update.effective_chat.id))
            image_path = await asyncio.to_thread(
                self.image_helper.search_and_replace,
                context.user_data["search_replace_image"],
                context.user_data["search_prompt"],
                context.user_data["replace_prompt"],
                "png",
            )
            progress_task.cancel()

            if not image_path:
                raise Exception("Search and replace operation failed")

            from io import BytesIO
            file_bytes = await asyncio.to_thread(lambda: open(image_path, "rb").read())
            file_obj = BytesIO(file_bytes)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_obj,
                caption="Here is your edited image with search and replace applied.",
            )
            await asyncio.to_thread(os.remove, image_path)
            await asyncio.to_thread(os.remove, context.user_data["search_replace_image"])

        except Exception as e:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            self.logger.error(f"Error in handle_replace_prompt: {e}")
            await update.effective_message.reply_text(
                "An error occurred during search and replace. Please try again later. If the problem persists, contact support."
            )
        return ConversationHandler.END

    @handle_errors
    async def inpaint_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Start the inpaint command conversation."""
        await self._update_last_message_time(context)
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text("Access denied. You are not authorized to use this bot.")
            return ConversationHandler.END

        await update.message.reply_text(
            "*Inpaint Image*\n\n"
            "Send me an image and a mask, then describe what you want to generate in the masked areas.\n\n"
            "The mask should be a black and white image where:\n"
            "• White areas = areas to fill in (inpaint)\n"
            "• Black areas = areas to keep unchanged\n\n"
            "Send the image or type /cancel to abort.",
            parse_mode="Markdown"
        )
        return ConversationState.WAITING_FOR_INPAINT_IMAGE

    @handle_errors
    async def handle_inpaint_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the image input for inpaint command."""
        await self._update_last_message_time(context)

        if update.message.text == "/skip":
            context.user_data["inpaint_image"] = None
        else:
            try:
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                file_path = f"./image/{photo.file_id}_inpaint.jpg"
                await asyncio.wait_for(file.download_to_drive(file_path), timeout=60)
                context.user_data["inpaint_image"] = file_path
            except asyncio.TimeoutError:
                await update.message.reply_text("Image download timed out. Please try again.")
                return ConversationHandler.END
            except Exception as e:
                self.logger.error(f"Error during inpaint image download: {e}")
                await update.message.reply_text("Failed to download image. Please try again.")
                return ConversationHandler.END

        await update.message.reply_text(
            "Now send a mask image that shows which parts of the image to inpaint (fill in).\n\n"
            "The mask should be the same size as your image and use:\n"
            "• White pixels = areas to generate new content\n"
            "• Black pixels = areas to keep unchanged\n\n"
            "Send the mask image or type /cancel to abort."
        )
        return ConversationState.WAITING_FOR_INPAINT_MASK

    @handle_errors
    async def handle_inpaint_mask(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the mask input for inpaint command."""
        await self._update_last_message_time(context)

        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            mask_path = f"./image/{photo.file_id}_inpaint_mask.jpg"
            await asyncio.wait_for(file.download_to_drive(mask_path), timeout=60)
            context.user_data["inpaint_mask"] = mask_path
        except asyncio.TimeoutError:
            await update.message.reply_text("Mask download timed out. Please try again.")
            return ConversationHandler.END
        except Exception as e:
            self.logger.error(f"Error during inpaint mask download: {e}")
            await update.message.reply_text("Failed to download mask. Please try again.")
            return ConversationHandler.END

        await update.message.reply_text(
            "Describe what you want to generate in the masked areas.\n\n"
            "Example: 'a beautiful forest', 'a modern city skyline', 'a cozy living room'\n\n"
            "Type your description or /cancel to abort."
        )
        return ConversationState.WAITING_FOR_INPAINT_PROMPT

    @handle_errors
    async def handle_inpaint_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle the prompt and perform inpaint operation."""
        await self._update_last_message_time(context)
        context.user_data["inpaint_prompt"] = update.message.text

        await update.message.reply_text("Processing your inpaint request...")

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )

            progress_task = asyncio.create_task(self._send_progress_update(context.bot, update.effective_chat.id))
            image_path = await asyncio.to_thread(
                self.image_helper.inpaint_image,
                context.user_data["inpaint_image"],
                context.user_data["inpaint_mask"],
                context.user_data["inpaint_prompt"],
                "png",
            )
            progress_task.cancel()

            if not image_path:
                raise Exception("Inpaint operation failed")

            from io import BytesIO
            file_bytes = await asyncio.to_thread(lambda: open(image_path, "rb").read())
            file_obj = BytesIO(file_bytes)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_obj,
                caption="Here is your inpainted image.",
            )
            await asyncio.to_thread(os.remove, image_path)
            await asyncio.to_thread(os.remove, context.user_data["inpaint_image"])
            await asyncio.to_thread(os.remove, context.user_data["inpaint_mask"])

        except Exception as e:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            self.logger.error(f"Error in handle_inpaint_prompt: {e}")
            await update.effective_message.reply_text(
                "An error occurred during inpainting. Please try again later. If the problem persists, contact support."
            )
        return ConversationHandler.END
