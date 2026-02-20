import os
import re
import base64
import requests
from io import BytesIO
from urllib.parse import urljoin
import trafilatura
from bs4 import BeautifulSoup
from PIL import Image
from transliterate import translit
from helpers.logger import logger

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB total
MAX_IMAGE_SIZE = 1 * 1024 * 1024  # 1MB per image
MIN_IMAGE_SIZE = 2 * 1024  # skip tiny tracking pixels

storage = "attachments" if os.environ.get("POOLING", "false").lower() == "true" else "/tmp"


class HTMLParser:
    def __init__(self, link: str):
        self.link = link
        self._downloaded = None
        self._extracted_html = None

    # ------------------------
    # Download page
    # ------------------------
    def _download(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(
            self.link,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )
        response.raise_for_status()

        # IMPORTANT: update canonical link
        self.link = response.url

        logger.info(f"Final resolved URL: {self.link}")

        self._downloaded = response.text
        return self._downloaded

    # ------------------------
    # Extract article HTML
    # ------------------------
    def _extract(self):
        if not self._downloaded:
            self._download()

        extracted = trafilatura.extract(
            self._downloaded,
            output_format="html",
            include_links=True,
            include_images=True,
            include_formatting=True,
        )

        if not extracted:
            raise ValueError("Article extraction failed")

        self._extracted_html = extracted
        return extracted

    # ------------------------
    # Process images for Kindle (1-bit PNG inline)
    # ------------------------
    def _process_image_monochrome_png(self, img_url, max_width=800):
        """Download image, convert to 1-bit PNG, return base64 data URL."""
        try:
            absolute_url = urljoin(self.link, img_url)
            response = requests.get(absolute_url, timeout=10)
            if response.status_code != 200:
                return None

            image_bytes = response.content
            image_size = len(image_bytes)
            if image_size < MIN_IMAGE_SIZE or image_size > MAX_IMAGE_SIZE:
                return None

            img = Image.open(BytesIO(image_bytes))

            # Resize if needed
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)

            # Convert to 1-bit monochrome
            img = img.convert("1")

            # Save to buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return f"data:image/png;base64,{encoded}"
        except Exception as e:
            logger.warning(f"Failed processing image {img_url}: {e}")
            return None

    def _inline_images(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        total_size = len(html.encode("utf-8"))

        for img in soup.find_all("img"):
            src = img.get("src")
            if not src:
                img.decompose()
                continue

            data_url = self._process_image_monochrome_png(src)
            if not data_url:
                img.decompose()
                continue

            projected_size = total_size + len(data_url.encode("utf-8"))
            if projected_size > MAX_FILE_SIZE:
                logger.info("Skipping image due to total HTML size limit")
                img.decompose()
                continue

            img["src"] = data_url
            total_size = projected_size

        final_html = str(soup)
        if len(final_html.encode("utf-8")) > MAX_FILE_SIZE:
            raise ValueError("Final HTML exceeds 5MB limit")

        return final_html

    # ------------------------
    # Header (safe filename)
    # ------------------------
    @property
    def header(self) -> str:
        if not self._downloaded:
            self._download()
        metadata = trafilatura.extract_metadata(self._downloaded)
        title = metadata.title if metadata and metadata.title else "article"
        raw_header = "_".join(title.split())
        clean_header = re.sub(r"[^\w\-_.]", "", raw_header)
        try:
            return translit(clean_header, language_code="ru", reversed=True)
        except Exception:
            return clean_header

    @property
    def kindle_html(self) -> str:
        return f"{storage}/{self.header}.html"

    # ------------------------
    # Generate final HTML
    # ------------------------
    def generate_kindle_html(self) -> str:
        extracted_html = self._extract()
        final_body = self._inline_images(extracted_html)
        final_html = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <title>{self.header}</title>
            </head>
            <body>
                {final_body}
            </body>
        </html>
        """

        if len(final_html.encode("utf-8")) > MAX_FILE_SIZE:
            raise ValueError("Generated file exceeds 5MB limit")

        file_path = self.kindle_html
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_html)

        logger.info(f"Saved article to {file_path}")
        return file_path


if __name__ == "__main__":
    # url = "https://u.habr.com/jYUSB"
    url = "https://www.freecodecamp.org/news/kubernetes-networking-tutorial-for-developers"
    parser = HTMLParser(url)
    parser.generate_kindle_html()
    print(f"Saved to: {parser.kindle_html}")