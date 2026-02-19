import requests
from bs4 import BeautifulSoup
import base64
from transliterate import translit
import os
from helpers.logger import logger

# set POOLING=true for local development - output will be saved to local attachments folder
storage = "attachments" if os.environ.get("POOLING", "false").lower() == "true" else "/tmp"
known_resources = 'habr.com',

class HTMLParser:
    def __init__(self, link):
        self.link = link

    @property
    def _resource(self):
        """Identify resource name from the link"""
        logger.info("Attempting to get resource name from link")
        logger.info(self.link)
        resource = self.link.split('/')[2]
        logger.info(f"Got Resource: {resource}")
        if resource in known_resources:
            return resource
        else:
            logger.error("Resource not known")

    @property
    def _containers(self):
        """Element selectors based on resource"""
        containers = {
            'habr.com': {
                "text": (
                    "h1.tm-title.tm-title_h1 span",  # header CSS selector
                    "div.article-formatted-body > div"  # body CSS selector
                ),
                "body": "div.article-formatted-body > div"  # body element for full HTML
            }
        }
        return containers.get(self._resource)

    def _raw_text(self, header=False):
        response = requests.get(self.link)
        soup = BeautifulSoup(response.content, 'html.parser')
        logger.debug("!!!!!!!!Got content for parse!!!!!!!!!!!!!!")
        logger.debug(soup)
        if header:
            header_selector = self._containers["text"][0]
            header_element = soup.select_one(header_selector)
            return header_element.get_text() if header_element else ""
        else:
            body_selector = self._containers["text"][1]
            body_elements = soup.select(body_selector)
            return " ".join([el.get_text() for el in body_elements])

    @property
    def header(self):
        raw_header = "_".join(self._raw_text(header=True).split())
        restricted_symbols = ["?", "!", ":"]
        clean_header = ''.join(filter(lambda x: x not in restricted_symbols, raw_header))
        return clean_header

    @property
    def kindle_html(self):
        return f"{storage}/{translit(self.header, language_code='ru', reversed=True)}.html"

    def generate_kindle_html(self):
        response = requests.get(self.link)
        soup = BeautifulSoup(response.content, 'html.parser')
        element = soup.select_one(self._containers["body"])

        if not element:
            print("No body element found!")
            return

        # Extract text
        text = element.get_text()

        # Extract images
        image_links = [img['src'] for img in element.find_all('img')]

        # Replace image src with base64
        for image_link in image_links:
            try:
                image_response = requests.get(image_link)
                if image_response.status_code == 200:
                    image_data = image_response.content
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    img_tag = element.find("img", src=image_link)
                    if img_tag:
                        new_tag = soup.new_tag("img", src=f"data:image/jpeg;base64,{base64_data}")
                        img_tag.replace_with(new_tag)
            except Exception as e:
                print(f"Error downloading image from {image_link}: {e}")

        # Save final HTML
        final_html_content = f"<html><body>{text}{str(element)}</body></html>"
        with open(self.kindle_html, 'w', encoding='utf-8') as file:
            file.write(final_html_content)


if __name__ == "__main__":
    url = 'https://habr.com/ru/articles/740778/'
    # article = HTMLParser(url)
    # article.generate_kindle_html()
    print(storage)
