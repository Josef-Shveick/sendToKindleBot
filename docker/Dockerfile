FROM amazon/aws-lambda-python:3.13

WORKDIR /var/task

# Copy your bot code
COPY bot.py html_parser.py send_to_kindle.py requirements.txt helpers ./
ADD helpers helpers

# Install dependencies
RUN python3 -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Set Lambda handler
CMD ["bot.handler"]
