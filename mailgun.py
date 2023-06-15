import requests
from env.env_reader import secrets


def send_mailgun(attachment_name, text='Destroy All Humans'):
    with open(f'attachments/{attachment_name}', 'rb') as attachment:
        return requests.post(
            f"https://api.mailgun.net/v3/{secrets['MAILGUN_SANDBOX']}.mailgun.org/messages",
            auth=("api", secrets["MAILGUN_API"]),
            files=[('attachment', (attachment_name, attachment.read()))],
            data={
                "from": f"Mailgun Sandbox <postmaster@{secrets['MAILGUN_SANDBOX']}.mailgun.org>",
                "to": f"Josef Shveick <{secrets['TEST_MAIL2']}>",
                "subject": "",
                "text": text
            },
        )

# if __name__ == "__main__":
