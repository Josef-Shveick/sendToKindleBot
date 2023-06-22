import requests
from bs4 import BeautifulSoup
from lxml import etree
import base64
from transliterate import translit


class HTMLParser:

    def __init__(self, link):
        self.link = link

    @property
    def _resource(self):
        """identify resource name, basing on provided link"""
        return self.link.split('/')[2]

    @property
    def _containers(self):
        """pick up element container selectors, basing on resource name"""
        containers = {
            'habr.com': {"text":  # xpath selectors
                             ('//h1[@class="tm-title tm-title_h1"]/span/text()',
                              "//div[starts-with(@xmlns,'http://www.w3.org/')]/text()"),
                         # CSS selector
                         "body": "div[class^='article-formatted-body'] > div"
                         }
        }
        return containers[self._resource]

    def _raw_text(self, header=False):
        response = requests.get(self.link)
        soup = BeautifulSoup(response.content, 'lxml')
        tree = etree.HTML(str(soup))
        xpath_expression = self._containers["text"][0] if header else self._containers["text"][1]
        text_elements = tree.xpath(xpath_expression)
        return ' '.join(text_elements)

    @property
    def header(self):
        raw_header = '_'.join(self._raw_text(header=True).split())
        restricted_symbols = ["?", "!", ":"]
        clean_header = ''.join(filter(lambda x: x not in restricted_symbols, raw_header))
        return clean_header

    @property
    def kindle_html(self):
        return f"attachments/{translit(self.header, language_code='ru', reversed=True)}.html"

    def generate_kindle_html(self):
        response = requests.get(self.link)
        soup = BeautifulSoup(response.content, 'html.parser')
        element = soup.select_one(self._containers["body"])

        # Extract the text from the element
        text = element.get_text()

        # Extract the image links from the element
        image_links = [img['src'] for img in element.find_all('img')]

        # replace image links with uploaded binary in result html
        for i, image_link in enumerate(image_links):
            try:
                print(image_link)
                image_response = requests.get(image_link)
                if image_response.status_code == 200:
                    image_data = image_response.content
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    element_copy = BeautifulSoup(str(element), 'html.parser')  # Create a copy of the element
                    image_tag = element_copy.find('img', src=image_link)
                    new_image_tag = soup.new_tag('img', src=f"data:image/jpeg;base64,{base64_data}")
                    if image_tag:
                        image_tag.replace_with(new_image_tag)
                        element = BeautifulSoup(str(element_copy), 'html.parser')  # Update the main element
            except Exception as e:
                print(f"Error downloading image from {image_link}: {str(e)}")

        # Create the final HTML content with the extracted text and updated image links
        final_html_content = f"<html><body>{text}{str(element)}</body></html>"

        # Save the final HTML content to the output file
        with open(self.kindle_html, 'w', encoding='utf-8') as file:
            file.write(final_html_content)


if __name__ == '__main__':
    url = 'https://habr.com/ru/articles/740778/'
    article = HTMLParser(url)
    article.generate_kindle_html()
