from helpers.logger import logger
import telebot
from io import BytesIO
import requests
import os
import json

from send_to_kindle import send_email, TELEBOT_KEY
from html_parser import HTMLParser

# Create an instance of the bot
bot = telebot.TeleBot(TELEBOT_KEY)

# --- MODE SELECTION ---
POOLING = os.environ.get("POOLING", "false").lower() == "true"

# Webhook URL for Lambda deployment
WEBHOOK_BASE_URL = os.environ.get("AWS_LAMBDA_FUNCTION_URL") or os.environ.get("WEBHOOK_BASE_URL")
WEBHOOK_URL = f"{WEBHOOK_BASE_URL.rstrip('/')}/{TELEBOT_KEY}/" if WEBHOOK_BASE_URL else None

# This flag ensures we only set webhook once per cold start
_webhook_checked = False

# --- WEBHOOK SETUP FUNCTION ---
def set_webhook():
    """Register Telegram webhook once (idempotent)."""
    global _webhook_checked
    if _webhook_checked or not WEBHOOK_URL:
        return

    try:
        get_info_url = f"https://api.telegram.org/bot{TELEBOT_KEY}/getWebhookInfo"
        set_url = f"https://api.telegram.org/bot{TELEBOT_KEY}/setWebhook"

        info = requests.get(get_info_url, timeout=10)
        info.raise_for_status()
        data = info.json()

        if data.get("ok") and data["result"].get("url") == WEBHOOK_URL:
            logger.info(f"Webhook already set to {WEBHOOK_URL}")
            _webhook_checked = True
            return

        resp = requests.post(set_url, data={"url": WEBHOOK_URL}, timeout=10)
        resp.raise_for_status()

        if resp.json().get("ok"):
            logger.info(f"Webhook set successfully to {WEBHOOK_URL}")
        else:
            logger.info(f"Failed to set webhook: {resp.text}")

    except Exception as e:
        logger.info(f"Error while setting webhook: {e}")

    _webhook_checked = True

# --- BOT HANDLERS ---

# Handle the /start command
@bot.message_handler(commands=['start'])
def start(message):
    username = message.from_user.username
    bot.reply_to(message, f"Yo {username}! What's up?")


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
            email_sent = send_email(article.kindle_html, message_text, message.from_user.username)

            if email_sent:
                bot.send_message(message.chat.id, "HTML sent to kindle successfully.")
            else:
                bot.send_message(message.chat.id, "Failed to send HTML to kindle.")
    else:
        bot.send_message(message.chat.id, "No file or links found in the message.")


@bot.message_handler(content_types=['document'])
def process_file(message):
    files = [message.document]
    username = message.from_user.username
    for file in files:
        file_name = file.file_name

        if not file_name.endswith('.epub'):
            bot.send_message(message.chat.id, f"Unsupported file format. Only .epub files accepted")
            return

        file_info = bot.get_file(file.file_id)
        bot.send_message(message.chat.id, f"File found: {file_name}.\nAttempting to send to {username} kindle...")

        try:
            downloaded_file = bot.download_file(file_info.file_path)
            file_buffer = BytesIO(downloaded_file)  # In-memory file-like object not to save file to disk
        except Exception as e:
            bot.send_message(message.chat.id, f"Error downloading file: {str(e)}")
            return

        file_sent = send_email(file_buffer, file_name, username)
        if file_sent:
            bot.send_message(message.chat.id, f"{file_name} sent to {username} kindle successfully.")
        else:
            bot.send_message(message.chat.id, f"Failed to send {file_name} to {username} kindle.")


# --- AWS LAMBDA HANDLER ---
def handler(event, context):
    """
    AWS Lambda entrypoint.
    Receives Telegram webhook updates as event["body"]
    """
    set_webhook()  # ensure webhook is set once

    try:
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)

        update = telebot.types.Update.de_json(body)
        bot.process_new_updates([update])

        return {"statusCode": 200, "body": json.dumps({"ok": True})}

    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# --- LOCAL DEVELOPMENT ---
if POOLING:  # for local development/test if there's no external url for webhook
    logger.info("Starting bot in polling mode...")
    bot.polling(interval=10)
