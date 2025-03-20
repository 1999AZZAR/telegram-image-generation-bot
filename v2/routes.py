from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
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

from helper import AuthHelper, ImageHelper
from models import ConversationState, ImageConfig, GenerationParams, ReimagineParams


class TelegramRoutes:
    def __init__(self, auth_helper, image_helper):
        self.auth_helper = auth_helper
        self.image_helper = image_helper
        self.logger = logging.getLogger(__name__)

    async def _update_last_message_time(self, context: ContextTypes.DEFAULT_TYPE):
        """Updates the last message time in user_data."""
        context.user_data["last_message_time"] = time.time()

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._update_last_message_time(context)
        """Handles the /start command to introduce the bot and its features."""
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return

        welcome_message = (
            f"🌟 Welcome, {update.effective_user.first_name}!\n\n"
            "I'm your AI-powered image assistant. Here's what I can do for you:\n\n"
            "🎨 *Generate Images*: Use /image to create AI-generated artwork from text prompts.\n"
            "🔄 *Reimagine Images*: Use /reimagine to transform an existing image based on a new concept.\n"
            "📈 *Upscale Images*: Use /upscale to enhance image quality and resolution.\n\n"
            "🚀 *How to Use Me:*\n"
            "1️⃣ Choose a command (/image, /reimagine, or /upscale).\n"
            "2️⃣ Follow the steps to provide the necessary details (prompt, style, image, etc.).\n"
            "3️⃣ Wait for me to generate your result!\n\n"
            "Use /help for more details about each feature."
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._update_last_message_time(context)
        """Displays a help message with all available bot commands."""
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return

        help_text = (
            "🤖 *AI Image Assistant - Commands Guide*\n\n"
            "🎨 */image* - Generate a new AI image from a text description.\n"
            "🔄 */reimagine* - Modify an existing image based on a new concept.\n"
            "📈 */upscale* - Enhance the resolution and quality of an image.\n"
            "⚙️ */set_watermark* - Toggle watermarking (Admins only).\n"
            "❌ */cancel* - Cancel the current operation.\n\n"
            "✨ *Tips for Best Results:*\n"
            "• Be detailed in your prompts for more accurate results.\n"
            "• Specify styles, moods, and compositions when needed.\n"
            "• Try different sizes and aspect ratios for better framing.\n\n"
            "Need help? Just start a command and follow the instructions! 🚀"
        )

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def set_watermark_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._update_last_message_time(context)
        """Displays current watermark status and allows admin to toggle it."""
        user_id = str(update.message.from_user.id)

        if not self.auth_helper.is_admin(user_id):
            await update.message.reply_text(
                "❌ You are not authorized to change this setting."
            )
            return

        # Get current status
        status = "ON ✅" if self.image_helper.watermark_enabled else "OFF ❌"

        # Inline keyboard buttons
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

    async def watermark_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._update_last_message_time(context)
        """Handles admin button clicks for watermark toggle."""
        query = update.callback_query
        await query.answer()

        if not self.auth_helper.is_admin(str(query.from_user.id)):
            await query.edit_message_text(
                "❌ You are not authorized to change this setting."
            )
            return

        # Toggle watermark based on button pressed
        if query.data == "set_watermark_on":
            self.image_helper.set_watermark_status(True)
            new_status = "ON ✅"
        else:
            self.image_helper.set_watermark_status(False)
            new_status = "OFF ❌"

        # Update message with new status
        await query.edit_message_text(
            f"⚙️ *Watermark Status Updated:* {new_status}", parse_mode="Markdown"
        )

    async def image_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        context.user_data[
            "current_state"
        ] = "WAITING_FOR_PROMPT"  # Track the current state
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

    async def handle_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        context.user_data["prompt"] = update.message.text
        context.user_data[
            "current_state"
        ] = "WAITING_FOR_CONTROL_TYPE"  # Track the current state

        # Ask user whether they want Regular or Control-Based generation
        keyboard = ReplyKeyboardMarkup(
            [["Regular", "Control-Based"]], one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text(
            "🖼️ Choose the generation type:", reply_markup=keyboard
        )

        return ConversationState.WAITING_FOR_CONTROL_TYPE

    async def handle_control_type(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        choice = update.message.text
        context.user_data["generation_type"] = choice
        context.user_data[
            "current_state"
        ] = "WAITING_FOR_SIZE"  # Track the current state

        if choice == "Control-Based":
            await update.message.reply_text("📤 Please upload the reference image.")
            return ConversationState.WAITING_FOR_IMAGE
        else:
            # Proceed with normal image size selection
            image_config = ImageConfig()
            keyboard = ReplyKeyboardMarkup(
                image_config.SIZE_PRESETS, one_time_keyboard=True, resize_keyboard=True
            )
            await update.message.reply_text(
                "📐 Select image size:", reply_markup=keyboard
            )
            return ConversationState.WAITING_FOR_SIZE

    async def handle_size(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        context.user_data["size"] = update.message.text
        context.user_data[
            "current_state"
        ] = "WAITING_FOR_STYLE"  # Track the current state

        # Instantiate ImageConfig
        image_config = ImageConfig()
        keyboard = ReplyKeyboardMarkup(
            image_config.STYLE_PRESETS, one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text("🎭 Select image style:", reply_markup=keyboard)
        return ConversationState.WAITING_FOR_STYLE

    async def handle_style(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles style selection for both image generation and creative upscaling."""
        style = update.message.text
        context.user_data["style"] = style

        generation_type = context.user_data.get("generation_type")
        if "current_state" in context.user_data:
            del context.user_data["current_state"]  # Clear the current state

        if generation_type == "Reimagine":
            # Handle reimagine flow
            await update.message.reply_text(
                "✨ Reimagining your image...", reply_markup=ReplyKeyboardRemove()
            )

            try:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
                )

                params = ReimagineParams(
                    prompt=context.user_data.get("prompt", ""),
                    control_image=context.user_data.get("control_image", ""),
                    style=style,
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
                self.logger.error(f"Error in handle_style (Reimagine): {e}")
                await update.message.reply_text(
                    "❌ Sorry, there was an error reimagining your image. Please try again."
                )

        elif (
            generation_type == "Upscale"
            and context.user_data.get("upscale_method") == "creative"
        ):
            # Handle creative upscaling flow
            await update.message.reply_text(
                "📷 Please send the image you want to upscale.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationState.WAITING_FOR_IMAGE

        else:
            # Handle regular image generation flow
            await update.message.reply_text(
                "🎨 Generating your image...", reply_markup=ReplyKeyboardRemove()
            )

            try:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
                )

                params = GenerationParams(
                    prompt=context.user_data.get("prompt", ""),
                    style=style,
                    size=context.user_data.get("size", "square"),
                    control_image=context.user_data.get("control_image", None),
                )

                image_path = self.image_helper.generate_image(params)

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
                self.logger.error(f"Error in handle_style (Image Generation): {e}")
                await update.message.reply_text(
                    "❌ Sorry, there was an error generating your image. Please try again."
                )

        return ConversationHandler.END

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
        keyboard = ReplyKeyboardMarkup(
            [["Conservative", "Creative", "Fast"]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await update.message.reply_text(
            "🖼️ Choose the upscaling method (Conservative, Creative, Fast):",
            reply_markup=keyboard,
        )

        return ConversationState.WAITING_FOR_UPSCALE_METHOD

    async def handle_upscale_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the input of the upscaling prompt."""
        context.user_data["upscale_prompt"] = update.message.text

        # If the method is "creative", ask for a style preset
        if context.user_data.get("upscale_method") == "creative":
            image_config = ImageConfig()
            keyboard = ReplyKeyboardMarkup(
                image_config.STYLE_PRESETS,
                one_time_keyboard=True,
                resize_keyboard=True,
            )
            await update.message.reply_text(
                "🎭 Select a style preset for creative upscaling:",
                reply_markup=keyboard,
            )
            return ConversationState.WAITING_FOR_STYLE
        else:
            # For "conservative" mode, proceed to ask for the image
            await update.message.reply_text(
                "📷 Please send the image you want to upscale."
            )
            return ConversationState.WAITING_FOR_IMAGE

    async def handle_upscale_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the selection of upscaling method (conservative, creative, fast)."""
        method = update.message.text.lower()
        if method not in ["conservative", "creative", "fast"]:
            await update.message.reply_text(
                "❌ Invalid method. Please choose 'Conservative', 'Creative', or 'Fast'."
            )
            return ConversationState.WAITING_FOR_UPSCALE_METHOD

        context.user_data["upscale_method"] = method

        if method in ["conservative", "creative"]:
            await update.message.reply_text("✏️ Please provide a prompt for upscaling.")
            return ConversationState.WAITING_FOR_UPSCALE_PROMPT
        else:
            # For "fast" mode, proceed to ask for the image
            await update.message.reply_text(
                "📷 Please send the image you want to upscale."
            )
            return ConversationState.WAITING_FOR_IMAGE

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
                keyboard = ReplyKeyboardMarkup(
                    image_config.STYLE_PRESETS,
                    one_time_keyboard=True,
                    resize_keyboard=True,
                )
                await update.message.reply_text(
                    "🎭 Select a style for reimagining:", reply_markup=keyboard
                )
                return ConversationState.WAITING_FOR_STYLE

            elif generation_type == "Control-Based":
                context.user_data["control_image"] = file_path
                image_config = ImageConfig()
                keyboard = ReplyKeyboardMarkup(
                    image_config.SIZE_PRESETS,
                    one_time_keyboard=True,
                    resize_keyboard=True,
                )
                await update.message.reply_text(
                    "📐 Select image size:", reply_markup=keyboard
                )
                return ConversationState.WAITING_FOR_SIZE

            elif generation_type == "Upscale":
                context.user_data["image"] = file_path
                keyboard = ReplyKeyboardMarkup(
                    [["webp", "jpeg", "png"]],
                    one_time_keyboard=True,
                    resize_keyboard=True,
                )
                await update.message.reply_text(
                    "📁 Select output format:", reply_markup=keyboard
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

    async def handle_format(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles image upscaling and sends back the result as a file."""
        upscale_method = context.user_data.get("upscale_method", "fast")

        if upscale_method == "creative":
            await update.message.reply_text(
                "🔄 Upscaling your image using the creative method... This may take a few moments. Please wait.",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await update.message.reply_text(
                "🔄 Upscaling your image...", reply_markup=ReplyKeyboardRemove()
            )

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
            )

            image_path = context.user_data.get("image", "")
            output_format = update.message.text
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
            await update.message.reply_text(
                "❌ Sorry, there was an error upscaling your image. Please try again."
            )
            if "current_state" in context.user_data:
                del context.user_data["current_state"]  # Clear the current state

        return ConversationHandler.END

    async def cancel_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        await update.message.reply_text(
            "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
        )
        if "current_state" in context.user_data:
            del context.user_data["current_state"]  # Clear the current state
        return ConversationHandler.END

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
        keyboard = ReplyKeyboardMarkup(
            [["Image", "Sketch"]], one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text(
            "🖼️ Choose the method (Image or Sketch):", reply_markup=keyboard
        )

        return ConversationState.WAITING_FOR_METHOD

    async def handle_reimagine_style(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Stores the selected style and asks for a reimagine description."""
        context.user_data["style"] = update.message.text
        await update.message.reply_text("✏️ Now provide a description for reimagining.")
        return ConversationState.WAITING_FOR_PROMPT

    async def handle_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        await self._update_last_message_time(context)
        """Handles the selection of method (Image or Sketch)."""
        method = update.message.text.lower()
        if method not in ["image", "sketch"]:
            await update.message.reply_text(
                "❌ Invalid method. Please choose 'Image' or 'Sketch'."
            )
            return ConversationState.WAITING_FOR_METHOD

        context.user_data["method"] = method
        await update.message.reply_text("📤 Please upload the image or sketch.")
        return ConversationState.WAITING_FOR_IMAGE

    async def handle_reimagine_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await self._update_last_message_time(context)
        """Handles reimagine prompt input and starts image transformation."""
        await update.message.reply_text(
            "✨ Reimagining your image...", reply_markup=ReplyKeyboardRemove()
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
            await update.message.reply_text(
                "❌ Sorry, there was an error reimagining your image. Please try again."
            )
            if "current_state" in context.user_data:
                del context.user_data["current_state"]  # Clear the current state

        return ConversationHandler.END
