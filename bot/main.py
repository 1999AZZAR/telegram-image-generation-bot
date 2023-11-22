import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from helper import generate_image  # Import the generate_image function from helper.py

# Load environment variables
load_dotenv()
api_key = os.getenv('STABILITY_API_KEY')
token = os.getenv('TELEGRAM_BOT_TOKEN') 

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# State constants
WAITING_FOR_PROMPT, WAITING_FOR_STYLE, PROCESSING = range(3)

# Function to handle the /image command
def image(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat_id

    # Ask the user for a prompt
    update.message.reply_text("Please enter a prompt for the image generation:")

    # Set the state to 'WAITING_FOR_PROMPT'
    context.user_data['state'] = WAITING_FOR_PROMPT

    return WAITING_FOR_PROMPT


# Function to handle text messages
def handle_text(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat_id

    # Check the state
    if 'state' in context.user_data and context.user_data['state'] == WAITING_FOR_PROMPT:
        # Get the user input (prompt)
        prompt = update.message.text

        # Save the prompt in the user data
        context.user_data['prompt'] = prompt

        # Ask the user for a style using a custom one-time keyboard
        style_keyboard = [
            ["photographic", "enhance", "anime"],
            ["digital-art", "comic-book", "fantasy-art"],
            ["line-art", "analog-film", "neon-punk"],
            ["isometric", "low-poly", "origami"],
            ["modeling-compound", "cinematic", "3d-model"],
            ["pixel-art", "tile-texture"]
        ]

        reply_markup = ReplyKeyboardMarkup(style_keyboard, one_time_keyboard=True)
        update.message.reply_text("Please select a style for the image:", reply_markup=reply_markup)

        # Set the state to 'WAITING_FOR_STYLE'
        context.user_data['state'] = WAITING_FOR_STYLE

        return WAITING_FOR_STYLE

    elif 'state' in context.user_data and context.user_data['state'] == WAITING_FOR_STYLE:
        # Get the user input (style)
        style = update.message.text

        # Get the saved prompt from user data
        prompt = context.user_data.get('prompt', '')

        # Set the state to 'PROCESSING'
        context.user_data['state'] = PROCESSING

        # Send "Processing..." message and remove the one-time keyboard
        reply_markup = ReplyKeyboardRemove()
        update.message.reply_text("Processing...", reply_markup=reply_markup)

        # Generate the image using the function from helper.py
        generated_image_path = generate_image(prompt, style)

        # Send the generated image to the user
        with open(generated_image_path, "rb") as f:
            context.bot.send_photo(chat_id, photo=f)

        # Log the successful image generation
        logger.info(f"Image successfully generated and sent to user {chat_id}")

        return ConversationHandler.END  # End the conversation

    # If the state is not 'WAITING_FOR_PROMPT' or 'WAITING_FOR_STYLE', return the current state
    return context.user_data.get('state', WAITING_FOR_PROMPT)

# Create the conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('image', image)],
    states={
        WAITING_FOR_PROMPT: [MessageHandler(Filters.text & ~Filters.command, handle_text)],
        WAITING_FOR_STYLE: [MessageHandler(Filters.text & ~Filters.command, handle_text)],
    },
    fallbacks=[],
)

# Set up the Telegram bot
updater = Updater(token)
dispatcher = updater.dispatcher

# Add command handlers
dispatcher.add_handler(CommandHandler("image", image))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
dispatcher.add_handler(MessageHandler(Filters.regex(r'^(photographic|enhance|anime|digital-art|comic-book|fantasy-art|line-art|analog-film|neon-punk|isometric|low-poly|origami|modeling-compound|cinematic|3d-model|pixel-art|tile-texture)$'), handle_text))
dispatcher.add_handler(conv_handler)

# Start the bot
updater.start_polling()
updater.idle()
