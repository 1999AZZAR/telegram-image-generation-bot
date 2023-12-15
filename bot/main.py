import os
import logging
import telegram
import threading

from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatAction

from helper import image_gen, helper_code
from telegram.error import NetworkError

class BotHandler:
    connection_alive = True 

    def __init__(self):
        load_dotenv('env')
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.updater = Updater(self.bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.helper = helper_code

        self.image_gen = image_gen
        self.WAITING_FOR_PROMPT, self.WAITING_FOR_SIZE, self.WAITING_FOR_STYLE, self.PROCESSING = range(4)
        self.conv_handler = ConversationHandler(
            entry_points=[CommandHandler('image', self.image)],
            states={
                self.WAITING_FOR_PROMPT: [MessageHandler(Filters.text & ~Filters.command, self.handle_image_prompt)],
                self.WAITING_FOR_SIZE: [MessageHandler(Filters.text & ~Filters.command, self.handle_image_size)],
                self.WAITING_FOR_STYLE: [MessageHandler(Filters.text & ~Filters.command, self.handle_image_style)],
            },
            fallbacks=[],
        )

    def _add_command_handlers(self):
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(self.conv_handler)

    def _add_error_handler(self):
        self.dispatcher.add_error_handler(self.error_handler)

    def error_handler(self, update, context):
        logging.error(f"Error occurred: {context.error}")
        if update.message:
            update.message.reply_text("Sorry, something went wrong. Please try again later.")
        else:
            logging.warning("Update message is None. Unable to send error message to the user.")

    def connection_watchdog(self):
        while True:
            try:
                self.updater.bot.get_me()
                if not self.connection_alive:
                    logging.info("Connection reestablished.")
                    self.connection_alive = True
            except NetworkError:
                if self.connection_alive:
                    logging.error("Connection lost. Attempting to reconnect...")
                    self.connection_alive = False
                    self.updater.start_polling(drop_pending_updates=True)

    def send_chat_action(self, update, context, action):
        try:
            context.bot.send_chat_action(chat_id=update.effective_chat.id, action=action)
        except telegram.error.TimedOut:
            logging.error("Timed out while sending chat action. Ignoring and continuing.")

    def get_user_id(self, update):
        return (update.callback_query.from_user.id if update.callback_query and update.callback_query.from_user else None) or \
            (update.message.from_user.id if update.message and update.message.from_user else None)

    def start(self, update, context):
        user_id = update.message.from_user.id
        self.send_chat_action(update, context, ChatAction.TYPING)
        if self.helper.is_user(user_id):
            logging.info(f"User selected the /start command")
            message = f"🌸 Greetings {update.message.from_user.first_name}, I'm a stability-powered Telegram bot. Use \"/image\" command to start generating an image. Let's explore the world of possibilities together!"
        else:
            message = "Apologies, you lack the necessary authorization to utilize my services."
        update.message.reply_text(text=message, parse_mode="MARKDOWN")

    def image(self, update, context):
        user_id = update.message.from_user.id
        logging.info(f"Image generation from {update.message.from_user.first_name}")
        chat_id = update.message.chat_id
        if self.helper.is_user(user_id):
            update.message.reply_text("Please enter a prompt for the image generation:")
            context.user_data['state'] = self.WAITING_FOR_PROMPT
            return self.WAITING_FOR_PROMPT
        else:
            update.message.reply_text("Apologies, you lack the necessary authorization to utilize my services.")
            return ConversationHandler.END

    def handle_image_prompt(self, update, context):
        chat_id = update.message.chat_id
        if 'state' in context.user_data and context.user_data['state'] == self.WAITING_FOR_PROMPT:
            prompt = update.message.text
            context.user_data['prompt'] = prompt
            size_keyboard = [
                ["landscape", "widescreen", "panorama"],
                ["square-l", "square", "square-p"],
                ["portrait", "highscreen", "panorama-p"]
            ]
            reply_markup = ReplyKeyboardMarkup(size_keyboard, one_time_keyboard=True)
            update.message.reply_text("Please select the preferred size for the image:", reply_markup=reply_markup)
            context.user_data['state'] = self.WAITING_FOR_SIZE
            return self.WAITING_FOR_SIZE

    def handle_image_size(self, update, context):
        chat_id = update.message.chat_id
        if 'state' in context.user_data and context.user_data['state'] == self.WAITING_FOR_SIZE:
            size = update.message.text
            context.user_data['size'] = size
            style_keyboard = [
                ["photographic", "enhance", "anime"],
                ["digital-art", "comic-book", "fantasy-art"],
                ["line-art", "analog-film", "neon-punk"],
                ["isometric", "low-poly", "origami"],
                ["modeling-compound", "cinematic", "3d-model"],
                ["pixel-art", "tile-texture", "None"]
            ]
            reply_markup = ReplyKeyboardMarkup(style_keyboard, one_time_keyboard=True)
            update.message.reply_text("Please select a style for the image:", reply_markup=reply_markup)
            context.user_data['state'] = self.WAITING_FOR_STYLE
            return self.WAITING_FOR_STYLE

    def handle_image_style(self, update, context):
        chat_id = update.message.chat_id
        if 'state' in context.user_data and context.user_data['state'] == self.WAITING_FOR_STYLE:
            style = update.message.text
            prompt = context.user_data.get('prompt', '')
            size = context.user_data.get('size', 'square')
            context.user_data['state'] = self.PROCESSING
            reply_markup = ReplyKeyboardRemove()
            logging.info("Generating image...")
            message = update.message.reply_text("Processing...", reply_markup=reply_markup)
            generated_image_path = self.image_gen.generate_image(prompt, style, size)
            if generated_image_path:
                self.send_chat_action(update, context, ChatAction.UPLOAD_PHOTO)
                with open(generated_image_path, "rb") as f:
                    context.bot.send_photo(chat_id, photo=f)
                context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                os.remove(generated_image_path)
                logging.info(f"Image successfully generated and sent to user {chat_id}")
            else:
                logging.error(f"Error generating image for user {chat_id}")
                context.bot.send_message(chat_id, "Sorry, there was an error generating the image. Please try again using another prompt.")
            return ConversationHandler.END
        return context.user_data.get('state', self.WAITING_FOR_PROMPT)

    def run(self):
        self._add_command_handlers()
        self._add_error_handler()
        self.updater.start_polling()
        logging.info("The bot has started")
        logging.info("The bot is listening for messages")
        threading.Thread(target=self.connection_watchdog, daemon=True).start()
        self.updater.idle()

if __name__ == "__main__":
    bot_handler = BotHandler()
    bot_handler.run()
