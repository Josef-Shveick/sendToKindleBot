import logging
import telebot

from send_to_kindle import send_email
from env.env_reader import secrets
from text_parser import TextParser, save_to_html

# Create an instance of the bot
bot = telebot.TeleBot(secrets['TELEBOT_KEY'])


# Handle the /start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Feed me")


# Handle incoming messages
@bot.message_handler(func=lambda message: True)
def process_message(message):
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

    # Send the links back to the user
    if links:
        for link in links:
            bot.send_message(message.chat.id, "Some links found. sending email")
            article = TextParser(link)
            attachment_name = f'{article.header}.html'
            email = send_email(attachment_name)
            print(email.status_code)
            print(email.text)
    else:
        bot.send_message(message.chat.id, "No hidden links found in the message.")


# Start the bot
bot.polling(interval=10)
