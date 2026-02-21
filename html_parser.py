import os
import base64
import requests
import trafilatura
from bs4 import BeautifulSoup
from transliterate import translit
from urllib.parse import urljoin
import re
from PIL import Image
from io import BytesIO

from helpers.logger import logger

storage = "attachments" if os.environ.get("POOLING", "false").lower() == "true" else "/tmp"

class HTMLParser:

    def __init__(self, link: str):
        self.link = link
        self.downloaded = trafilatura.fetch_url(link)

        if not self.downloaded:
            raise ValueError("Failed to download the page")

        self.header = self._generate_header()
        self.filename = f"{self.header}.html"


    def _generate_header(self) -> str:
        """
        Generate a safe ASCII filename from the article title.
        """
        metadata = trafilatura.extract_metadata(self.downloaded)
        title = metadata.title if metadata and metadata.title else "article"

        # Replace spaces with underscores
        raw_header = "_".join(title.split())

        # Keep only ASCII letters, digits, underscore, dash, dot
        clean_header = re.sub(r"[^\w\-]", "", raw_header)
        header = clean_header[:50] if clean_header else "article"
        logger.info(f"Generated header: {header}")
        # Limit length for safety (optional)
        return header

    @property
    def kindle_html(self) -> str:
        return f"{storage}/{self.filename}"

    def _embed_images(self, soup: BeautifulSoup) -> None:
        """
        Replace <graphic> with optimized base64 JPEG images.
        Resize + compress for Kindle efficiency.
        """

        for img in soup.find_all("graphic"):
            src = img.get("src")
            if not src:
                continue

            try:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = urljoin(self.link, src)

                response = requests.get(src, timeout=10)
                if response.status_code != 200:
                    continue

                # Open image with Pillow
                image = Image.open(BytesIO(response.content))

                # Convert to RGB (required for JPEG)
                if image.mode in ("RGBA", "P"):
                    image = image.convert("L")

                # Resize if too wide (Kindle-friendly width)
                max_width = 800
                if image.width > max_width:
                    ratio = max_width / image.width
                    new_height = int(image.height * ratio)
                    image = image.resize((max_width, new_height), Image.LANCZOS)

                # Save optimized JPEG to memory buffer
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=60, optimize=True)

                base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

                new_img_tag = soup.new_tag("img", src=f"data:image/jpeg;base64,{base64_data}")
                img.replace_with(new_img_tag)

            except Exception as e:
                logger.info(f"Image optimization failed: {src} -> {e}")

    def generate_kindle_html(self) -> None:
        """
        Generate minimal Kindle-compatible HTML.
        """
        extracted_html = trafilatura.extract(
            self.downloaded,
            include_images=True,
            include_links=False,
            include_comments=False,
            output_format="html"
        )

        if not extracted_html:
            raise ValueError("Failed to extract article content")

        soup = BeautifulSoup(extracted_html, "html.parser")

        # Embed images directly into HTML
        self._embed_images(soup)

        # Only inner HTML (avoid double <html>/<body>)
        body_content = ''.join(str(tag) for tag in soup.body.contents) if soup.body else str(soup)

        final_html = f"""<html>
<head>
<meta charset="UTF-8">
<title>{self.header}</title>
</head>
<body>{body_content}</body>
</html>"""

        with open(self.kindle_html, "w", encoding="utf-8") as f:
            f.write(final_html)
            logger.info(f"html contents written to file: {self.kindle_html}")


if __name__ == "__main__":
    url = "https://u.habr.com/uOtAm"
    # url = "https://habr.com/ru/companies/gnivc/articles/983800/"
    # url = "https://www.freecodecamp.org/news/kubernetes-networking-tutorial-for-developers"
    article = HTMLParser(url)
    article.generate_kindle_html()