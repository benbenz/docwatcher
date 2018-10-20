from bs4 import BeautifulSoup
from selenium import webdriver
from urllib.parse import urlparse, urljoin
from selenium.webdriver.firefox.options import Options


def get_hrefs_html(response, follow_foreign_hosts=False):
    urls = []
    soup = BeautifulSoup(response.text, "lxml")
    parsed_response_url = urlparse(response.url)
    urls_on_page = [link.attrs.get("href") for link in soup.find_all('a')]

    for url in urls_on_page:
        follow = True
        parsed_url = urlparse(url)

        if not parsed_url.path:
            continue

        if not parsed_url.netloc:
            url = urljoin(response.url, parsed_url.path)
            parsed_url = urlparse(url)

        if parsed_response_url.netloc != parsed_url.netloc and not follow_foreign_hosts:
            follow = False

        urls.append({"url": url, "follow": follow})

    return urls


def handle_url_list_js(url_list, parsed_response_url, follow_foreign_hosts):
    urls = []

    for url in url_list:
        follow = True
        parsed_url = urlparse(url)

        if parsed_response_url.netloc != parsed_url.netloc and not follow_foreign_hosts:
            follow = False

        urls.append({"url": url, "follow": follow})

    return urls


def get_hrefs_js_simple(response, follow_foreign_hosts=False):
    parsed_response_url = urlparse(response.url)
    response.html.render()
    urls_on_page = response.html.absolute_links

    return handle_url_list_js(urls_on_page, parsed_response_url, follow_foreign_hosts)


def get_hrefs_js_complex(response, follow_foreign_hosts=False, executable_path='geckodriver'):
    urls = []
    parsed_response_url = urlparse(response.url)

    # Configure driver options
    driver_options = Options()
    driver_options.headless = True
    driver = webdriver.Firefox(executable_path=executable_path, options=driver_options)

    # Open url
    driver.get(response.url)

    clickable_elements = []

    elements = driver.find_elements_by_css_selector("*")

    # Go through all elements on page and look where the cursor is a pointer
    for element in elements:
        if element.value_of_css_property("cursor") == "pointer":
            if not element.get_attribute("href"):
                clickable_elements.append(element)

    # Repeat the following until there is no javascript element to click on
    # 1. Get urls of the page
    # 2. Click on one of the javascript elements

    if len(clickable_elements) == 0:
        urls_on_page = [link.get_attribute("href") for link in \
                        driver.find_elements_by_css_selector("a") \
                        if len(link.get_attribute("href")) > 0]
        driver.close()

        return handle_url_list_js(urls_on_page, parsed_response_url, follow_foreign_hosts)

    for i in range(len(clickable_elements)):
        urls_on_page = [link.get_attribute("href") for link in \
                        driver.find_elements_by_css_selector("a") \
                        if len(link.get_attribute("href")) > 0]

        urls += handle_url_list_js(urls_on_page, parsed_response_url, follow_foreign_hosts)

        clickable_elements[i].click()

    driver.close()

    return urls