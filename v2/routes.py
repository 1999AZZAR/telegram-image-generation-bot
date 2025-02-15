from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
import logging
import os

from models import ConversationState, ImageConfig, GenerationParams


class TelegramRoutes:
    def __init__(self, auth_helper, image_helper):
        self.auth_helper = auth_helper
        self.image_helper = image_helper
        self.logger = logging.getLogger(__name__)

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return

        welcome_message = (
            f"🌟 Welcome {update.effective_user.first_name}!\n\n"
            "I'm an AI-powered image generation bot. Here's how to use me:\n"
            "1. Use /image to start generating an image\n"
            "2. Provide a detailed prompt\n"
            "3. Select image size and style\n\n"
            "Use /help for more information."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self.auth_helper.is_user(str(update.message.from_user.id)):
            await update.message.reply_text(
                "🔒 Sorry, you are not authorized to use this bot."
            )
            return

        help_text = (
            "🎨 *Available Commands*\n"
            "/start - Start the bot\n"
            "/image - Generate a new image\n"
            "/help - Show this help message\n"
            "/cancel - Cancel current operation\n\n"
            "*Tips for better results:*\n"
            "• Be specific in your prompts\n"
            "• Include details about style, mood, and composition\n"
            "• Experiment with different sizes and styles"
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

        # Instantiate ImageConfig
        image_config = ImageConfig()
        print("SIZE_PRESETS:", image_config.SIZE_PRESETS)

        keyboard = ReplyKeyboardMarkup(
            image_config.SIZE_PRESETS, one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text("📐 Select image size:", reply_markup=keyboard)
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

    async def cancel_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        await update.message.reply_text(
            "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
