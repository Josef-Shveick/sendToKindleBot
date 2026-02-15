FROM python:3.15.0a6-alpine

WORKDIR /bot

COPY bot.py html_parser.py requirements.txt send_to_kindle.py helpers /bot/

RUN pip install --no-cache-dir --upgrade -r /bot/requirements.txt

CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "5000"]