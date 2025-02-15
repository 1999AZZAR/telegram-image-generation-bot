# main.py
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
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

        # Add conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("image", self.routes.image_command)],
            states={
                ConversationState.WAITING_FOR_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_prompt
                    )
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

        # Add handlers
        app.add_handler(CommandHandler("start", self.routes.start_command))
        app.add_handler(CommandHandler("help", self.routes.help_command))
        app.add_handler(conv_handler)

        return app

    def run(self):
        self.logger.info("Starting bot...")
        self.application.run_polling()


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
