import os
import base64
import requests
import trafilatura
from trafilatura.settings import use_config
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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

PROXY_DOMAINS = "medium.com",

SCRAPESTACK_KEY = os.environ.get("SCRAPESTACK_KEY")

_trafilatura_config = use_config()
_trafilatura_config.set("DEFAULT", "USER_AGENTS", BROWSER_HEADERS["User-Agent"])

storage = "attachments" if os.environ.get("POOLING", "false").lower() == "true" else "/tmp"


class HTMLParser:

    def __init__(self, link: str):
        self.link = link
        self.tmp_converted_svgs = dict()  # temporary storage for converted svg images

        logger.info(f"Parsing URL: {link}")
        self.downloaded = self._fetch(link)
        if not self.downloaded:
            logger.error(f"Failed to download: {link}")
            raise ValueError("Failed to download the page")

        if "medium.com" in self.link:
            self._fix_lazy_images()
        self._rewrite_svg_sources()

        self.header = self._generate_header()
        self.filename = f"{self.header}.html"

    @staticmethod
    def _needs_proxy(url: str) -> bool:
        hostname = urlparse(url).hostname or ""
        return any(domain in hostname for domain in PROXY_DOMAINS)

    @staticmethod
    def _fetch(url: str) -> str | None:
        """Download page directly, or via scrapestack for blocked domains."""
        if HTMLParser._needs_proxy(url):
            if not SCRAPESTACK_KEY:
                raise ValueError("SCRAPESTACK_KEY is not set")
            logger.info(f"Fetching via scrapestack: {url}")
            try:
                resp = requests.get(
                    "https://api.scrapestack.com/scrape",
                    params={"access_key": SCRAPESTACK_KEY, "url": url},
                    timeout=30,
                )
                resp.raise_for_status()
                if len(resp.text) > 512:
                    logger.info("scrapestack fetch succeeded")
                    return resp.text
                logger.warning(f"scrapestack response too short ({len(resp.text)} chars)")
            except Exception as e:
                logger.error(f"scrapestack fetch failed: {e}")

        logger.info(f"Fetching via trafilatura: {url}")
        return trafilatura.fetch_url(url, config=_trafilatura_config)

    def _fix_lazy_images(self) -> None:
        """
        Many sites (Medium, Substack, etc.) use <picture> with <source srcset>
        while keeping <img src=""> empty (lazy loading). Trafilatura only looks
        at <img src>, so these images get silently dropped.

        Fix: populate empty <img src> from the best <source srcset> URL
        before trafilatura sees the HTML.
        """
        soup = BeautifulSoup(self.downloaded, "html.parser")
        fixed = 0

        for picture in soup.find_all("picture"):
            img = picture.find("img")
            if not img or img.get("src"):
                continue

            best_url = None
            for source in picture.find_all("source"):
                srcset = source.get("srcset", "")
                if not srcset:
                    continue

                # srcset format: "url1 640w, url2 720w, url3 1080w"
                # pick the largest variant (last entry or highest width descriptor)
                candidates = []
                for part in srcset.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    tokens = part.split()
                    url = tokens[0]
                    width = 0
                    if len(tokens) > 1 and tokens[1].endswith("w"):
                        try:
                            width = int(tokens[1][:-1])
                        except ValueError:
                            pass
                    candidates.append((width, url))

                if candidates:
                    candidates.sort(key=lambda c: c[0], reverse=True)
                    # prefer non-webp source for broader compatibility
                    if source.get("type") == "image/webp" and best_url:
                        continue
                    best_url = candidates[0][1]

            if best_url:
                img["src"] = best_url
                fixed += 1
                logger.info(f"Fixed lazy image src: {best_url[:100]}")

        # also fix standalone <img> with empty src but data-src or srcset
        for img in soup.find_all("img"):
            if img.get("src"):
                continue

            data_src = img.get("data-src") or img.get("data-lazy-src") or img.get("data-original")
            if data_src:
                img["src"] = data_src
                fixed += 1
                logger.info(f"Fixed data-src image: {data_src[:100]}")
                continue

            srcset = img.get("srcset", "")
            if srcset:
                first_url = srcset.split(",")[0].strip().split()[0]
                if first_url:
                    img["src"] = first_url
                    fixed += 1
                    logger.info(f"Fixed srcset image: {first_url[:100]}")

        if fixed:
            self.downloaded = str(soup)
            logger.info(f"Fixed {fixed} lazy-loaded image(s)")

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
                logger.warning(f"SVG rewrite failed: {src} -> {e}")

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
                        logger.warning(f"Image skipped (HTTP {response.status_code}): {src}")
                        continue

                    image = Image.open(BytesIO(response.content))

                image = image.convert("L")

                # Resize
                max_width = 800
                if image.width > max_width:
                    ratio = max_width / image.width
                    new_height = int(image.height * ratio)
                    image = image.resize((max_width, new_height), Image.LANCZOS)

                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=80, optimize=True)

                base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

                # Always replace tag with <img>, Kindle not displays <graphic>
                new_img = soup.new_tag(
                    "img",
                    src=f"data:image/jpeg;base64,{base64_data}"
                )

                tag.replace_with(new_img)

            except Exception as e:
                logger.warning(f"Image embedding failed: {src} -> {e}")

    # ---------------------------------------------------------

    def generate_kindle_html(self) -> None:
        logger.info(f"Extracting article content: {self.link}")

        extracted_html = trafilatura.extract(
            self.downloaded,
            include_images=True,
            include_links=False,
            include_comments=False,
            output_format="html"
        )

        if not extracted_html:
            logger.error(f"Trafilatura extraction returned empty result: {self.link}")
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
    url3 = "https://issaouiadam.medium.com/the-kubelet-deep-dive-understanding-pod-startup-failures-155f94ba7433"

    # article1 = HTMLParser(url1)
    # article1.generate_kindle_html()

    # article2 = HTMLParser(url2)
    # article2.generate_kindle_html()

    # article3 = HTMLParser(url3)
    # article3.generate_kindle_html()