"""Select the delivery destination without changing existing email behavior."""

from send_to_dropbox import send_to_dropbox
from send_to_kindle import send_email


def delivery_destination(username):
    return "Dropbox" if username == "Josef_Shveick" else "Kindle"


def send_file(file_obj, filename, username):
    if delivery_destination(username) == "Dropbox":
        return send_to_dropbox(file_obj, filename)
    return send_email(file_obj, filename, username)
