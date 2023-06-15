import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from env.env_reader import secrets

# Email configuration
SMTP_SERVER = secrets["SMTP_SERVER"]
SMTP_PORT = secrets["SMTP_PORT"]
SMTP_USERNAME = secrets["TEST_MAIL"]
SMTP_PASSWORD = secrets["TEST_MAIL_PWD"]
SENDER_EMAIL = secrets["TEST_MAIL"]
RECIPIENT_EMAIL = secrets["KINDLE_MAIL"]


def send_email():
    # Create the email message
    subject = 'Hello from Python'
    body = 'This is the body of the email.'

    # Create a multipart message
    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = SENDER_EMAIL
    message['To'] = RECIPIENT_EMAIL

    # Add the body text to the message
    message.attach(MIMEText(body, 'plain'))

    # Load the attachment file
    attachment_path = 'attachments/output.html'
    with open(attachment_path, 'rb') as attachment_file:
        attachment = MIMEApplication(attachment_file.read())

    # Set the attachment filename
    attachment_filename = 'kray_vselennoi.html'
    attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)

    # Add the attachment to the message
    message.attach(attachment)

    # Connect to the SMTP server and send the email
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)


if __name__ == "__main__":
    send_email()
