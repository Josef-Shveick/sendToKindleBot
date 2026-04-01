import os
import base64
import requests
import trafilatura
from trafilatura.settings import use_config
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from PIL import Image
from io import BytesIO
import cairosvg
import uuid

from helpers.logger import logger

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "*",
}

_trafilatura_config = use_config()
_trafilatura_config.set("DEFAULT", "USER_AGENTS", BROWSER_HEADERS["User-Agent"])

storage = "attachments" if os.environ.get("POOLING", "false").lower() == "true" else "/tmp"


class HTMLParser:

    def __init__(self, link: str):
        self.link = link
        self.tmp_converted_svgs = dict()  # temporary storage for converted svg images

        self.downloaded = trafilatura.fetch_url(link, config=_trafilatura_config)
        if not self.downloaded:
            raise ValueError("Failed to download the page")

        self._rewrite_svg_sources()

        self.header = self._generate_header()
        self.filename = f"{self.header}.html"

    def _rewrite_svg_sources(self) -> None:
        """
        trafilatura looses .svg images during html extraction, so
        Before trafilatura extraction:
        If img/graphic src contains .svg → convert to PNG
        and rewrite ONLY src value.
        """
        soup = BeautifulSoup(self.downloaded, "html.parser")

        for tag in soup.find_all(["img", "graphic", "picture"]): # update possible image tags list as needed
            src = tag.get("src")
            if not src or ".svg" not in src.lower():
                continue

            try:
                src = urljoin(self.link, src)

                # handle protocol relative urls like //site.com/img.png
                if src.startswith("//"):
                    src = "https:" + src

                response = requests.get(src, timeout=15, headers=BROWSER_HEADERS)
                response.raise_for_status()

                png_bytes = cairosvg.svg2png(
                    bytestring=response.content,
                    output_width=800
                )

                temp_png_object_name = f"{uuid.uuid4().hex}.png"
                self.tmp_converted_svgs.update({temp_png_object_name:png_bytes})

                # update src value to point to converted image object in tmp dict storage
                tag["src"] = temp_png_object_name

                logger.info(f"Rewrote SVG src to PNG: {src}")

            except Exception as e:
                logger.info(f"SVG rewrite failed: {src} -> {e}")

        self.downloaded = str(soup)

    # ---------------------------------------------------------

    def _generate_header(self) -> str:
        metadata = trafilatura.extract_metadata(self.downloaded)
        title = metadata.title if metadata and metadata.title else "article"

        raw_header = "_".join(title.split())
        clean_header = re.sub(r"[^\w\-]", "", raw_header)
        header = clean_header[:50] if clean_header else "article"

        logger.info(f"Generated header: {header}")
        return header

    @property
    def kindle_html(self) -> str:
        return f"{storage}/{self.filename}"


    def _embed_images(self, soup: BeautifulSoup) -> None:
        """
        Update html extracted by trafilatura.
        Encode images to base64 and embed rewriting src value in graphic tags.
        """

        # trafilatura converts all img contained tags to graphic
        for tag in soup.find_all("graphic"):
            src = tag.get("src")
            if not src:
                continue

            try:
                image_bytes = self.tmp_converted_svgs.pop(src, None)

                if image_bytes: # if image was converted from svg and stored in tmp dict
                    image = Image.open(BytesIO(image_bytes))
                else:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = urljoin(self.link, src)

                    response = requests.get(src, timeout=10, headers=BROWSER_HEADERS)
                    if response.status_code != 200:
                        continue

                    image = Image.open(BytesIO(response.content))

                # Convert to grayscale (Kindle friendly)
                if image.mode in ("RGBA", "P"):
                    image = image.convert("L")

                # Resize
                max_width = 800
                if image.width > max_width:
                    ratio = max_width / image.width
                    new_height = int(image.height * ratio)
                    image = image.resize((max_width, new_height), Image.LANCZOS)

                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=60, optimize=True)

                base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

                # Always replace tag with <img>, Kindle not displays <graphic>
                new_img = soup.new_tag(
                    "img",
                    src=f"data:image/jpeg;base64,{base64_data}"
                )

                tag.replace_with(new_img)

            except Exception as e:
                logger.info(f"Image embedding failed: {src} -> {e}")

    # ---------------------------------------------------------

    def generate_kindle_html(self) -> None:

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

        # Encode images to base64
        self._embed_images(soup)

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
    url1 = "https://habr.com/ru/companies/gnivc/articles/983800/"
    url2 = "https://learnkube.com/etcd-breaks-at-scale"

    article1 = HTMLParser(url1)
    article1.generate_kindle_html()

    article2 = HTMLParser(url2)
    article2.generate_kindle_html()