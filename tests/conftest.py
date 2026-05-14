import os

# These env vars are read by send_to_kindle.py at module import time.
# setdefault preserves real values if you have them in your local shell
# (so manual `python bot.py` runs aren't affected), and provides safe
# dummies in CI where nothing is set.
os.environ.setdefault("SMTP_SERVER", "smtp.example.com")
os.environ.setdefault("SMTP_PORT", "465")
os.environ.setdefault("TEST_MAIL", "test@example.com")
os.environ.setdefault("TEST_MAIL_PWD", "dummy")
os.environ.setdefault("TELEBOT_KEY", "dummy")

# POOLING must be "false" or `import bot` calls bot.polling() at module level
# (bot.py line 229) and the test process hangs forever. Force-override.
os.environ["POOLING"] = "false"
