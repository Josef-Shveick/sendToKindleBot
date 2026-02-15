FROM public.ecr.aws/lambda/python:3.11

COPY bot.py html_parser.py requirements.txt send_to_kindle.py helpers ./

RUN pip install --no-cache-dir --upgrade -r /bot/requirements.txt

CMD ["bot.handler"]