import requests
from env.env_reader import secrets


def send_email(link):
    return requests.post(
        f"https://api.mailgun.net/v3/{secrets['MAILGUN_SANDBOX']}.mailgun.org/messages",
        auth=("api", secrets["MAILGUN_API"]),
        data={"from": f"Mailgun Sandbox <postmaster@{secrets['MAILGUN_SANDBOX']}.mailgun.org>",
              "to": f"Josef Shveick <{secrets['TEST_MAIL']}>",
              "subject": "Link Found",
              "text": link})


# if __name__ == "__main__":
