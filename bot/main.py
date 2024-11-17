from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import os
import logging
from dotenv import load_dotenv
import threading

from helper import image_gen, helper_code


class BotHandler:
    def __init__(self):
        load_dotenv("env")
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.helper = helper_code
        self.image_gen = image_gen

        self.WAITING_FOR_PROMPT, self.WAITING_FOR_SIZE, self.WAITING_FOR_STYLE, self.PROCESSING = range(4)

        self.application = Application.builder().token(self.bot_token).build()

        self.conv_handler = ConversationHandler(
            entry_points=[CommandHandler("image", self.image)],
            states={
                self.WAITING_FOR_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_image_prompt)],
                self.WAITING_FOR_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_image_size)],
                self.WAITING_FOR_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_image_style)],
            },
            fallbacks=[],
        )

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(self.conv_handler)

    async def send_chat_action(self, update, context, action):
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=action)
        except Exception as e:
            logging.error(f"Error while sending chat action: {e}")

    async def start(self, update, context):
        user_id = update.message.from_user.id
        if self.helper.is_user(user_id):
            logging.info("User selected the /start command")
            message = f"🌸 Greetings {update.message.from_user.first_name}, I'm a stability-powered Telegram bot. Use \"/image\" command to start generating an image. Let's explore the world of possibilities together!"
        else:
            message = "Apologies, you lack the necessary authorization to utilize my services."
        await update.message.reply_text(text=message)

    async def image(self, update, context):
        user_id = update.message.from_user.id
        if self.helper.is_user(user_id):
            await update.message.reply_text("Please enter a prompt for the image generation:")
            context.user_data["state"] = self.WAITING_FOR_PROMPT
            return self.WAITING_FOR_PROMPT
        else:
            await update.message.reply_text("Apologies, you lack the necessary authorization to utilize my services.")
            return ConversationHandler.END

    async def handle_image_prompt(self, update, context):
        prompt = update.message.text
        context.user_data["prompt"] = prompt
        size_keyboard = [
            ["landscape", "widescreen", "panorama"],
            ["square-l", "square", "square-p"],
            ["portrait", "highscreen", "panorama-p"],
        ]
        reply_markup = ReplyKeyboardMarkup(size_keyboard, one_time_keyboard=True)
        await update.message.reply_text("Please select the preferred size for the image:", reply_markup=reply_markup)
        return self.WAITING_FOR_SIZE

    async def handle_image_size(self, update, context):
        size = update.message.text
        context.user_data["size"] = size
        style_keyboard = [
            ["photographic", "enhance", "anime"],
            ["digital-art", "comic-book", "fantasy-art"],
            ["line-art", "analog-film", "neon-punk"],
            ["isometric", "low-poly", "origami"],
            ["modeling-compound", "cinematic", "3d-model"],
            ["pixel-art", "tile-texture", "None"],
        ]
        reply_markup = ReplyKeyboardMarkup(style_keyboard, one_time_keyboard=True)
        await update.message.reply_text("Please select a style for the image:", reply_markup=reply_markup)
        return self.WAITING_FOR_STYLE

    async def handle_image_style(self, update, context):
        style = update.message.text
        prompt = context.user_data.get("prompt", "")
        size = context.user_data.get("size", "square")
        reply_markup = ReplyKeyboardRemove()
        message = await update.message.reply_text("Processing...", reply_markup=reply_markup)

        generated_image_path = self.image_gen.generate_image(prompt, style, size)
        if generated_image_path:
            await self.send_chat_action(update, context, ChatAction.UPLOAD_PHOTO)
            with open(generated_image_path, "rb") as f:
                await context.bot.send_photo(update.message.chat_id, photo=f)
            os.remove(generated_image_path)
        else:
            await context.bot.send_message(update.message.chat_id, "Error generating image. Try another prompt.")
        return ConversationHandler.END

    def run(self):
        self.application.run_polling()


if __name__ == "__main__":
    bot_handler = BotHandler()
    bot_handler.run()
