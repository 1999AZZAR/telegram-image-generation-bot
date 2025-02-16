from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
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

from helper import AuthHelper, ImageHelper
from models import ConversationState, ImageConfig, GenerationParams, ReimagineParams


class TelegramRoutes:
    def __init__(self, auth_helper, image_helper):
        self.auth_helper = auth_helper
        self.image_helper = image_helper
        self.logger = logging.getLogger(__name__)

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
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
            "❌ */cancel* - Cancel the current operation.\n\n"
            "✨ *Tips for Best Results:*\n"
            "• Be detailed in your prompts for more accurate results.\n"
            "• Specify styles, moods, and compositions when needed.\n"
            "• Try different sizes and aspect ratios for better framing.\n\n"
            "Need help? Just start a command and follow the instructions! 🚀"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def image_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
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
        context.user_data["prompt"] = update.message.text

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
        choice = update.message.text
        context.user_data["generation_type"] = choice

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
        context.user_data["size"] = update.message.text

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
        await update.message.reply_text(
            "🎨 Generating your image...", reply_markup=ReplyKeyboardRemove()
        )

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
            )

            params = GenerationParams(
                prompt=context.user_data.get("prompt", ""),
                style=update.message.text,
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
            self.logger.error(f"Error in handle_style: {e}")
            await update.message.reply_text(
                "❌ Sorry, there was an error generating your image. Please try again."
            )

        return ConversationHandler.END

    async def upscale_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        """Handles /upscale command and asks user to send an image."""
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return ConversationHandler.END

        # ✅ Set correct generation type for /upscale
        context.user_data["generation_type"] = "Upscale"

        await update.message.reply_text("📷 Please send the image you want to upscale.")
        return ConversationState.WAITING_FOR_IMAGE

    async def handle_image(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        """Handles image upload for reimagine, upscale, and control-based generation."""
        try:
            self.logger.info("📸 User sent an image. Requesting file from Telegram...")

            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_path = f"./image/{photo.file_id}.jpg"

            self.logger.info(f"📥 Starting image download: {file_path}")
            await asyncio.wait_for(file.download_to_drive(file_path), timeout=60)

            self.logger.info(f"✅ Image successfully downloaded: {file_path}")

            generation_type = context.user_data.get(
                "generation_type"
            )  # Ensure we check for the correct type

            if generation_type == "Reimagine":
                context.user_data["control_image"] = file_path

                # ✅ Ask for style selection before prompt
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
                return (
                    ConversationState.WAITING_FOR_FORMAT
                )  # ✅ Correctly return WAITING_FOR_FORMAT for upscale

            else:
                # ❌ If `generation_type` is missing, send an error and reset
                self.logger.error("⚠️ Missing generation_type in context.")
                await update.message.reply_text(
                    "❌ Something went wrong. Please restart the command."
                )
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
            return ConversationHandler.END

    async def handle_format(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handles image upscaling and sends back the result as a file."""
        await update.message.reply_text(
            "🔄 Upscaling your image...", reply_markup=ReplyKeyboardRemove()
        )

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
            )

            image_path = context.user_data.get("image", "")
            output_format = update.message.text

            upscaled_image_path = self.image_helper.upscale_image(
                image_path, output_format
            )

            if not upscaled_image_path:
                raise Exception("Image upscaling failed")

            with open(upscaled_image_path, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=f"upscalled.{output_format}",  # ✅ Ensures correct filename when sending
                    caption="🖼️ Here's your upscaled image (sent as a file to preserve quality).",
                )

            os.remove(upscaled_image_path)

        except Exception as e:
            self.logger.error(f"Error in handle_format: {e}")
            await update.message.reply_text(
                "❌ Sorry, there was an error upscaling your image. Please try again."
            )

        return ConversationHandler.END

    async def cancel_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await update.message.reply_text(
            "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def reimagine_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        """Handles the /reimagine command."""
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return ConversationHandler.END

        # ✅ Ensure generation_type is set correctly
        context.user_data["generation_type"] = "Reimagine"

        await update.message.reply_text("📤 Please upload an image to reimagine.")
        return ConversationState.WAITING_FOR_IMAGE

    async def handle_reimagine_style(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> ConversationState:
        """Stores the selected style and asks for a reimagine description."""
        context.user_data["style"] = update.message.text
        await update.message.reply_text("✏️ Now provide a description for reimagining.")
        return ConversationState.WAITING_FOR_PROMPT

    async def handle_reimagine_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
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
                style=context.user_data.get(
                    "style", "None"
                ),  # Include user-selected style
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

        return ConversationHandler.END
