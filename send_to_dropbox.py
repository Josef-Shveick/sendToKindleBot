"""Dropbox delivery using credentials supplied through the environment."""

import json
import os
from io import BytesIO

import requests

from helpers.logger import logger


def send_to_dropbox(file_obj, filename):
    try:
        refresh_token = os.environ["DROPBOX_REFRESH_TOKEN"]
        app_key = os.environ["DROPBOX_APP_KEY"]
        if not refresh_token or not app_key:
            raise ValueError("Missing Dropbox credentials")

        # Never allow a supplied filename to escape the configured folder.
        filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
        if filename in ("", ".", ".."):
            raise ValueError("Invalid filename")
        folder = os.environ.get("DROPBOX_FOLDER", "").strip("/")
        if any(part in (".", "..") for part in folder.split("/")):
            raise ValueError("Invalid Dropbox folder")
        path = f"/{folder}/{filename}" if folder else f"/{filename}"

        if isinstance(file_obj, str):
            with open(file_obj, "rb") as source:
                content = source.read()
        elif isinstance(file_obj, BytesIO):
            file_obj.seek(0)
            content = file_obj.read()
        else:
            raise TypeError("Unsupported file object")

        # The simple upload endpoint supports files up to 150 MB.
        if len(content) > 150_000_000:
            raise ValueError("File exceeds Dropbox upload limit")

        credentials = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": app_key,
        }
        app_secret = os.environ.get("DROPBOX_APP_SECRET")
        if app_secret:
            credentials["client_secret"] = app_secret
        token_response = requests.post(
            "https://api.dropboxapi.com/oauth2/token",
            data=credentials,
            timeout=10,
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Invalid access token")

        response = requests.post(
            "https://content.dropboxapi.com/2/files/upload",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/octet-stream",
                "Dropbox-API-Arg": json.dumps({
                    "path": path,
                    "mode": "add",
                    "autorename": True,
                }),
            },
            data=content,
            timeout=15,
        )
        response.raise_for_status()
        logger.info("File uploaded to Dropbox successfully")
        return True
    except (KeyError, ValueError, TypeError, OSError, requests.RequestException) as error:
        # Exception text and HTTP bodies may contain credentials. Log only the type.
        logger.error("Dropbox delivery failed (%s)", type(error).__name__)
        return False
