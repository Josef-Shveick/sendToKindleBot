from helpers.logger import logger
import telebot
from io import BytesIO

from send_to_kindle import send_email, TELEBOT_KEY
from html_parser import HTMLParser

# Create an instance of the bot
bot = telebot.TeleBot(TELEBOT_KEY)


# Handle the /start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Feed me")


# Handle incoming messages
@bot.message_handler(func=lambda message: True)
def process_link(message):
    # Get the message text
    message_text = message.text

    # Get the entities in the message
    entities = message.entities

    # Extract hidden links from the message
    links = []
    if entities:
        for entity in entities:
            if entity.type == "text_link" and '.jpg' not in entity.url:
                links.append(entity.url)

    if links:
        logger.info(f"Some links found. Generating html for {links}")
        for link in links:
            bot.send_message(message.chat.id, "Some links found. Generating html")
            article = HTMLParser(link)
            article.generate_kindle_html()
            email_sent = send_email(article.kindle_html)

            if email_sent:
                bot.send_message(message.chat.id, "HTML sent to kindle successfully.")
            else:
                bot.send_message(message.chat.id, "Failed to send HTML to kindle.")
    else:
        bot.send_message(message.chat.id, "No file or links found in the message.")


@bot.message_handler(content_types=['document'])
def process_file(message):
    files = [message.document]
    for file in files:
        file_name = file.file_name

        if not file_name.endswith('.epub'):
            bot.send_message(message.chat.id, f"Unsupported file format. Only .epub files accepted")
            return

        file_info = bot.get_file(file.file_id)
        bot.send_message(message.chat.id, f"File found: {file_name}")

        try:
            downloaded_file = bot.download_file(file_info.file_path)
            file_buffer = BytesIO(downloaded_file)  # In-memory file-like object not to save file to disk
        except Exception as e:
            bot.send_message(message.chat.id, f"Error downloading file: {str(e)}")
            return

        file_sent = send_email(file_buffer, file_name)
        if file_sent:
            bot.send_message(message.chat.id, f"{file_name} sent to kindle successfully.")
        else:
            bot.send_message(message.chat.id, f"Failed to send {file_name}.")


# Start the bot
bot.polling(interval=10)
