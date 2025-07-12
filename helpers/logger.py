import os
import logging
from logging.handlers import RotatingFileHandler


LOGLEVEL = logging.DEBUG

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
log_file = os.path.join(parent_dir, "send_to_kindle_bot.log")


class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.msg = "[SEND_TO_KINDLE_BOT] " + str(record.msg)
        return super().format(record)


logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

console_handler = logging.StreamHandler()
console_handler.setLevel(LOGLEVEL)
formatter = CustomFormatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5 * 1024 * 1024, backupCount=0)
file_handler.setLevel(LOGLEVEL)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
