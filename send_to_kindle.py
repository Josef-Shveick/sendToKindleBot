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


def send_email(file):
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
    with open(file, 'rb') as attachment_file:
        attachment = MIMEApplication(attachment_file.read())

    # Set the attachment filename
    attachment.add_header('Content-Disposition', 'attachment', filename=file.split('/')[-1])

    # Add the attachment to the message
    message.attach(attachment)

    try:
        # Connect to the SMTP server and send the email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)

        # Email sent successfully
        return True
    except Exception as e:
        # An error occurred while sending the email
        print(f"Error sending email: {str(e)}")
        return False


if __name__ == "__main__":
    send_email('attachment/output.html')
