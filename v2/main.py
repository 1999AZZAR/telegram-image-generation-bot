import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackQueryHandler,
    JobQueue,
    ContextTypes,  # Import ContextTypes
)
from PIL import Image
from dotenv import load_dotenv
import os
import asyncio
import time  # Import time for timeout functionality

from models import ConversationState
from helper import AuthHelper, ImageHelper
from routes import TelegramRoutes

# Timeout duration in seconds
TIMEOUT_DURATION = 300  # 5 minutes


class TelegramBot:
    def __init__(self):
        load_dotenv()

        # Setup logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        self.logger = logging.getLogger(__name__)

        # Initialize helpers and routes
        self.auth_helper = AuthHelper()
        self.image_helper = ImageHelper()
        self.routes = TelegramRoutes(self.auth_helper, self.image_helper)

        # Setup application
        self.application = self._create_application()

    def _create_application(self) -> Application:
        app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

        # Add conversation handler for image generation
        conv_handler_image = ConversationHandler(
            entry_points=[CommandHandler("image", self.routes.image_command)],
            states={
                ConversationState.WAITING_FOR_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_prompt
                    )
                ],
                ConversationState.WAITING_FOR_CONTROL_TYPE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_control_type
                    )
                ],
                ConversationState.WAITING_FOR_IMAGE: [
                    MessageHandler(filters.PHOTO, self.routes.handle_image)
                ],
                ConversationState.WAITING_FOR_SIZE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_size
                    )
                ],
                ConversationState.WAITING_FOR_STYLE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_style
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
        )

        # Add conversation handler for image upscaling
        conv_handler_upscale = ConversationHandler(
            entry_points=[CommandHandler("upscale", self.routes.upscale_command)],
            states={
                ConversationState.WAITING_FOR_UPSCALE_METHOD: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_upscale_method,
                    )
                ],
                ConversationState.WAITING_FOR_UPSCALE_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_upscale_prompt,
                    )
                ],
                ConversationState.WAITING_FOR_STYLE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_style
                    )
                ],
                ConversationState.WAITING_FOR_IMAGE: [
                    MessageHandler(filters.PHOTO, self.routes.handle_image)
                ],
                ConversationState.WAITING_FOR_FORMAT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_format
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
        )

        # Add conversation handler for image reimaginer
        conv_handler_reimagine = ConversationHandler(
            entry_points=[CommandHandler("reimagine", self.routes.reimagine_command)],
            states={
                ConversationState.WAITING_FOR_METHOD: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_method
                    )
                ],
                ConversationState.WAITING_FOR_IMAGE: [
                    MessageHandler(filters.PHOTO, self.routes.handle_image)
                ],
                ConversationState.WAITING_FOR_STYLE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_reimagine_style,
                    )
                ],
                ConversationState.WAITING_FOR_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_reimagine_prompt,
                    )
                ],
                ConversationState.WAITING_FOR_FORMAT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_format
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
        )

        # Add all handlers
        app.add_handler(CommandHandler("start", self.routes.start_command))
        app.add_handler(CommandHandler("help", self.routes.help_command))
        app.add_handler(
            CommandHandler("set_watermark", self.routes.set_watermark_command)
        )
        app.add_handler(
            CallbackQueryHandler(
                self.routes.watermark_callback, pattern="set_watermark_.*"
            )
        )

        app.add_handler(conv_handler_image)
        app.add_handler(conv_handler_upscale)
        app.add_handler(conv_handler_reimagine)

        # Add job queue for timeout
        app.job_queue.run_repeating(self._check_timeout, interval=60.0)

        return app

    async def _check_timeout(self, context: ContextTypes.DEFAULT_TYPE):
        """Checks for conversations that have timed out and cancels them."""
        for chat_id, user_data in context.application.user_data.items():
            if "last_message_time" in user_data:
                elapsed_time = time.time() - user_data["last_message_time"]
                if elapsed_time > TIMEOUT_DURATION:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⏳ Your session has timed out due to inactivity. Please start over.",
                    )
                    user_data.clear()

    def run(self):
        self.logger.info("Starting bot...")
        self.application.run_polling()


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
