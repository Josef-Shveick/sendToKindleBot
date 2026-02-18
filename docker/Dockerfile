FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    calibre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data

ENTRYPOINT ["ebook-convert"]
