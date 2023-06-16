import requests
import base64
from bs4 import BeautifulSoup


def text_html(web_link, output_html_file='output.html'):
    response = requests.get(web_link)
    soup = BeautifulSoup(response.content, 'html.parser')
    element = soup.select_one("div[class^='article-formatted-body'] > div")

    # Extract the text from the element
    text = element.get_text()

    # Extract the image links from the element
    image_links = [img['src'] for img in element.find_all('img')]

    # Download and save the images as .jpg files
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
    with open(output_html_file, 'w', encoding='utf-8') as file:
        file.write(final_html_content)


if __name__ == "__main__":
    # Usage example
    link = ''
    text_html(link, output_html_file='attachments/output.html')
