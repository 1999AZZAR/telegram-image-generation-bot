import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackQueryHandler,
)
from PIL import Image
from dotenv import load_dotenv
import os

from models import ConversationState
from helper import AuthHelper, ImageHelper
from routes import TelegramRoutes


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
                ConversationState.WAITING_FOR_CONTROL_TYPE: [  # 🔥 Add this line
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
                ConversationState.WAITING_FOR_UPSCALE_METHOD: [  # State for method selection
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_upscale_method,
                    )
                ],
                ConversationState.WAITING_FOR_UPSCALE_PROMPT: [  # State for prompt input
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_upscale_prompt,
                    )
                ],
                ConversationState.WAITING_FOR_STYLE: [  # State for style selection (for creative mode)
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_style
                    )
                ],
                ConversationState.WAITING_FOR_IMAGE: [  # State for image upload
                    MessageHandler(filters.PHOTO, self.routes.handle_image)
                ],
                ConversationState.WAITING_FOR_FORMAT: [  # State for format selection
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
                ConversationState.WAITING_FOR_METHOD: [  # New state for method selection
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

        return app

    def run(self):
        self.logger.info("Starting bot...")
        self.application.run_polling()


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
