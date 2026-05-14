"""
Tests for the import of the bot, html_parser, and send_to_kindle modules.
More functional tests to be added later.
"""

def test_imports():
    import bot
    import html_parser
    import send_to_kindle


def test_handler_signature():
    from bot import handler
    assert callable(handler)
