import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackQueryHandler,
    JobQueue,
    ContextTypes,
)
from PIL import Image
from dotenv import load_dotenv
import sys
import os
import asyncio
import time
from colorlog import ColoredFormatter
from typing import Any

from models import ConversationState
from helper import AuthHelper, ImageHelper
from routes import TelegramRoutes

# Timeout duration in seconds
LOOP_TIMEOUT_DURATION = 60  # 1 minute for individual steps
STALL_TIMEOUT_DURATION = 180  # 3 minutes for overall inactivity


class TelegramBot:
    def __init__(self) -> None:
        load_dotenv()

        # Initialize logging
        self._setup_logging()

        # Initialize helpers and routes
        self.auth_helper = AuthHelper()
        self.image_helper = ImageHelper()
        self.routes = TelegramRoutes(self.auth_helper, self.image_helper)

        # Setup application
        self.application = self._create_application()

    def _setup_logging(self) -> None:
        """Set up logging with a custom format and suppress unnecessary logs."""
        # Create a logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Suppress logs from third-party libraries
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)

        # Create a console handler with colorized output (optional)
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
        console_handler.setFormatter(console_formatter)

        # Add the handler to the logger
        self.logger.addHandler(console_handler)

        # Log the start of the application
        self.logger.info("Logging setup complete. Starting bot...")

    def _create_application(self) -> Application:
        app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

        # Add conversation handler for image generation
        conv_handler_image = ConversationHandler(
            entry_points=[CommandHandler("imagine", self.routes.image_command)],
            states={
                ConversationState.WAITING_FOR_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_prompt
                    )
                ],
                ConversationState.WAITING_FOR_CONTROL_TYPE: [
                    CallbackQueryHandler(self.routes.handle_control_type)
                ],
                ConversationState.WAITING_FOR_IMAGE: [
                    MessageHandler(filters.PHOTO, self.routes.handle_image)
                ],
                ConversationState.WAITING_FOR_SIZE: [
                    CallbackQueryHandler(self.routes.handle_size)
                ],
                ConversationState.WAITING_FOR_STYLE: [
                    CallbackQueryHandler(self.routes.handle_style)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
            conversation_timeout=STALL_TIMEOUT_DURATION,
        )

        # Add conversation handler for image upscaling
        conv_handler_upscale = ConversationHandler(
            entry_points=[CommandHandler("upscale", self.routes.upscale_command)],
            states={
                ConversationState.WAITING_FOR_UPSCALE_METHOD: [
                    CallbackQueryHandler(self.routes.handle_upscale_method)
                ],
                ConversationState.WAITING_FOR_UPSCALE_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_upscale_prompt,
                    )
                ],
                ConversationState.WAITING_FOR_STYLE: [
                    CallbackQueryHandler(self.routes.handle_style)
                ],
                ConversationState.WAITING_FOR_IMAGE: [
                    MessageHandler(filters.PHOTO, self.routes.handle_image)
                ],
                ConversationState.WAITING_FOR_FORMAT: [
                    CallbackQueryHandler(self.routes.handle_format)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
            conversation_timeout=STALL_TIMEOUT_DURATION,
        )

        # Add conversation handler for image reimaginer
        conv_handler_reimagine = ConversationHandler(
            entry_points=[CommandHandler("reimagine", self.routes.reimagine_command)],
            states={
                ConversationState.WAITING_FOR_METHOD: [
                    CallbackQueryHandler(self.routes.handle_method)
                ],
                ConversationState.WAITING_FOR_IMAGE: [
                    MessageHandler(filters.PHOTO, self.routes.handle_image)
                ],
                ConversationState.WAITING_FOR_STYLE: [
                    CallbackQueryHandler(self.routes.handle_reimagine_style)
                ],
                ConversationState.WAITING_FOR_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_reimagine_prompt,
                    )
                ],
                ConversationState.WAITING_FOR_FORMAT: [
                    CallbackQueryHandler(self.routes.handle_format)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
            conversation_timeout=STALL_TIMEOUT_DURATION,
        )

        # Add conversation handler for the new /imagine_v2 command
        conv_handler_imagine_v2 = ConversationHandler(
            entry_points=[CommandHandler("imaginev2", self.routes.imagine_v2_command)],
            states={
                ConversationState.WAITING_FOR_PROMPT_V2: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.routes.handle_prompt_v2
                    )
                ],
                ConversationState.WAITING_FOR_ASPECT_RATIO_V2: [
                    CallbackQueryHandler(self.routes.handle_aspect_ratio_v2)
                ],
                ConversationState.WAITING_FOR_IMAGE_V2: [
                    MessageHandler(filters.PHOTO, self.routes.handle_image_v2),
                    CommandHandler("skip", self.routes.handle_image_v2),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
            conversation_timeout=STALL_TIMEOUT_DURATION,
        )

        # Add conversation handler for uncrop/outpaint
        conv_handler_uncrop = ConversationHandler(
            entry_points=[CommandHandler("uncrop", self.routes.uncrop_command)],
            states={
                ConversationState.WAITING_FOR_UNCROP_IMAGE: [
                    MessageHandler(filters.PHOTO, self.routes.handle_uncrop_image)
                ],
                ConversationState.WAITING_FOR_UNCROP_ASPECT_RATIO: [
                    CallbackQueryHandler(self.routes.handle_uncrop_aspect_ratio)
                ],
                ConversationState.WAITING_FOR_UNCROP_POSITION: [
                    CallbackQueryHandler(self.routes.handle_uncrop_position),
                    CommandHandler("skip", self.routes.handle_uncrop_position),
                ],
                ConversationState.WAITING_FOR_UNCROP_PROMPT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.routes.handle_uncrop_prompt,
                    ),
                    CommandHandler("skip", self.routes.handle_uncrop_prompt),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.routes.cancel_command)],
            conversation_timeout=STALL_TIMEOUT_DURATION,
        )

        # Add all handlers
        app.add_handler(CommandHandler("start", self.routes.start_command))
        app.add_handler(CommandHandler("help", self.routes.help_command))
        app.add_handler(
            CommandHandler("set_watermark", self.routes.set_watermark_command)
        )
        app.add_handler(
            CallbackQueryHandler(
                self.routes.watermark_callback, pattern="^set_watermark_"
            )
        )

        app.add_handler(conv_handler_image)
        app.add_handler(conv_handler_imagine_v2)
        app.add_handler(conv_handler_upscale)
        app.add_handler(conv_handler_reimagine)
        app.add_handler(conv_handler_uncrop)

        # Add job queue for timeout
        app.job_queue.run_repeating(
            self._check_timeout,
            interval=10.0,  # Run every 10 seconds
            first=10.0,  # Start after 10 seconds
        )

        return app

    async def _check_timeout(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Checks for conversations that have timed out and cancels them."""
        for chat_id, user_data in context.application.user_data.items():
            if "last_message_time" in user_data:
                elapsed_time = time.time() - user_data["last_message_time"]

                # Check for stall timeout (3 minutes of inactivity)
                if elapsed_time > STALL_TIMEOUT_DURATION:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Your session has timed out due to inactivity. Please start over.",
                    )
                    user_data.clear()  # Clear user data to reset the conversation
                    continue

                # Check for loop timeout (1 minute for individual steps)
                if (
                    "current_state" in user_data
                    and elapsed_time > LOOP_TIMEOUT_DURATION
                ):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="You took too long to respond. Please restart the current step.",
                    )
                    # Reset the last message time to give the user another chance
                    user_data["last_message_time"] = time.time()

    def run(self) -> None:
        self.logger.info("Starting bot...")
        self.application.run_polling()


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
