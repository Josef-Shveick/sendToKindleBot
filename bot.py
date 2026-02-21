from helpers.logger import logger
import telebot
from fastapi import FastAPI, Request
from mangum import Mangum
from io import BytesIO
import requests
import os
import re

from send_to_kindle import send_email, TELEBOT_KEY
from html_parser import HTMLParser

# --- BOT & FASTAPI INIT ---
bot = telebot.TeleBot(TELEBOT_KEY, threaded=False)
app = FastAPI()
handler = Mangum(app)

# --- GLOBAL FLAGS ---
POOLING = os.environ.get("POOLING", "false").lower() == "true"
_webhook_checked = False
_processed_update_ids = set()   # prevent duplicate processing


# --- BOT HANDLERS (always registered) ---

@bot.message_handler(commands=['start'])
def start(message):
    logger.info("Triggering start reply")
    username = message.from_user.username
    bot.reply_to(message, f"Yo, {username}! What's up?")


# unified handler to avoid missing content types
@bot.message_handler(func=lambda m: True, content_types=[
    "text", "photo", "document"
])
def process_message(message):

    logger.info("Received message")
    logger.info(f"Content type: {message.content_type}")

    username = message.from_user.username

    # -----------------------------
    # DOCUMENT HANDLING (.epub)
    # -----------------------------
    if message.content_type == "document":
        logger.info("Received document")

        file = message.document
        if not file:
            logger.warning("Document content_type but document is None")
            bot.send_message(message.chat.id, "Failed to process message content")
            return

        file_name = file.file_name
        logger.info(f"Document name: {file_name}")

        if not file_name.endswith(".epub"):
            bot.send_message(message.chat.id,
                             "Unsupported file format. Only .epub files accepted")
            return

        try:
            file_info = bot.get_file(file.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            file_buffer = BytesIO(downloaded_file)
        except Exception as e:
            logger.error(f"Error downloading file: {e}", exc_info=True)
            bot.send_message(message.chat.id,
                             f"Error downloading file: {str(e)}")
            return

        file_sent = send_email(file_buffer, file_name, username)
        if file_sent:
            bot.send_message(message.chat.id,
                             f"{file_name} sent to {username} Kindle successfully.")
        else:
            bot.send_message(message.chat.id,
                             f"Failed to send {file_name} to {username} Kindle.")
        return


    # ------------------------------------
    # TEXT / PHOTO CAPTION LINK HANDLING
    # ------------------------------------
    message_text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []

    links = extract_links(message_text, entities)

    if links:
        logger.info(f"Links found: {links}")
        for link in links:
            bot.send_message(message.chat.id,
                             "Some links found. Generating HTML")

            try:
                article = HTMLParser(link)
                article.generate_kindle_html()
                email_sent = send_email(
                    article.kindle_html,
                    article.filename,
                    username
                )

                if email_sent:
                    bot.send_message(message.chat.id,
                                     "HTML sent to Kindle successfully.")
                else:
                    bot.send_message(message.chat.id,
                                     "Failed to send HTML to Kindle.")

            except Exception as e:
                logger.error(f"Error processing link {link}: {e}",
                             exc_info=True)
                bot.send_message(message.chat.id,
                                 "Error processing the link.")
        return

    # ------------------------------------
    # FALLBACK
    # ------------------------------------
    bot.send_message(message.chat.id, "No file or links found in the message.")


def extract_links(message_text, entities) -> list[str]:
    links = set()

    # 1. Use Telegram entities
    for entity in entities or []:
        if entity.type == "url":
            beginning = entity.offset
            end = beginning + entity.length
            links.add(message_text[beginning:end])
        elif entity.type == "text_link" and entity.url:
            links.add(entity.url)

    # 2. always add regex matches (deduplicated by set)
    regex_links = re.findall(r'https?://[^\s<>"\]\)]+', message_text or "")
    links.update(regex_links)

    # 3. Filter out local/internal addresses
    forbidden_patterns = ("127.0.0.1", "localhost", "169.254.169.254")
    safe_links = [l for l in links if not any(host in l for host in forbidden_patterns)]

    return safe_links


# --- WEBHOOK SETUP (for AWS Lambda) ---
if not POOLING:

    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

    def set_webhook():
        global _webhook_checked
        if _webhook_checked:
            return

        get_info_url = f"https://api.telegram.org/bot{TELEBOT_KEY}/getWebhookInfo"
        set_url = f"https://api.telegram.org/bot{TELEBOT_KEY}/setWebhook"

        try:
            info = requests.get(get_info_url, timeout=10)
            info.raise_for_status()
            data = info.json()

            if data.get("ok") and data["result"].get("url") == WEBHOOK_URL:
                logger.info(f"Webhook already set to {WEBHOOK_URL}")
                _webhook_checked = True
                return

            resp = requests.post(set_url,
                                 data={"url": WEBHOOK_URL},
                                 timeout=10)
            resp.raise_for_status()

            if resp.json().get("ok"):
                logger.info(f"Webhook set successfully to {WEBHOOK_URL}")
            else:
                logger.info(f"Failed to set webhook: {resp.text}")

        except Exception as e:
            logger.error(f"Error while setting webhook: {e}",
                         exc_info=True)

        _webhook_checked = True


    @app.on_event("startup")
    def on_startup():
        set_webhook()


    @app.post("/SendToKindleBot")
    async def telegram_webhook(request: Request):

        try:
            json_data = await request.json()
            logger.info("Received new request")
            logger.info(json_data)

            update = telebot.types.Update.de_json(json_data)

            # duplicate protection
            if update.update_id in _processed_update_ids:
                logger.info(f"Ignoring duplicate update {update.update_id}")
                return {"ok": True}

            _processed_update_ids.add(update.update_id)
            if len(_processed_update_ids) > 1000:
                _processed_update_ids.pop()

            logger.info(f"Processing request {update.update_id}")

            bot.process_new_updates([update])

            return {"ok": True}

        except Exception as e:
            logger.error(f"Error processing request: {e}",
                         exc_info=True)
            return {"error": str(e)}


# --- LOCAL POLLING (for dev) ---
if POOLING:
    logger.info("Starting bot in polling mode...")
    bot.polling(interval=3)
