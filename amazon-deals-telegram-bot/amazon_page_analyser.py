from selenium import webdriver

from selenium.webdriver.chrome.service import Service  # handle chromium driver
from selenium.webdriver.common.by import By  # get element by

import re  # use regex for selecting product id in link
import time  # wait until new page loaded

import requests  # lighter way to retrieve information from html only (no js and css loaded)
from lxml import html


def start_selenium():
    chromium_options = webdriver.ChromeOptions()  # add the debug options you need
    chromium_options.add_argument("--headless")  # do not open chromium gui
    chromium_options.add_argument('--disable-gpu')  # disable hardware acceleration for compatibility reasons

    # create a Chromium tab with the selected options
    chromium_driver = webdriver.Chrome(executable_path=r"path\to\chromedriver.exe", options=chromium_options)

    return chromium_driver


def get_all_deals_ids():
    selenium_driver = start_selenium()
    deals_ids = get_deals_page_ids(selenium_driver)  # get deals only once
    selenium_driver.quit()  # close everything that was created. Better not to keep driver open for much time
    return deals_ids  # could be None or could contain the deals ids


def get_deals_page_ids(selenium_driver):
    deals_page = "https://www.amazon.it/deals/"

    print("Starting taking all urls")

    try:
        selenium_driver.get(deals_page)

        # go to page with 50% or more discount
        selenium_driver.execute_script("arguments[0].click();",
                                       selenium_driver.find_element(By.PARTIAL_LINK_TEXT,
                                                                    "Sconto del 50%"))  # not using full text to avoid problems with utf-8

        # get all deals (products and submenus)
        elements_urls = []
        emergency_counter = 0

        while len(elements_urls) == 0:  # wait until pages loads the products with the wanted discount
            # get all urls with <a> tag with a css class that contains 'DealCard'. There are both immediate deals and submenus with deals
            elements_urls = [e.get_attribute("href") for e in
                             selenium_driver.find_elements(By.CSS_SELECTOR, "a[class*='DealCard']")]
            time.sleep(0.5)

            emergency_counter += 1  # avoid infinite loop if page does not load
            if emergency_counter > 120:
                raise Exception("Error loading products in deals page")

        deals_urls = []  # store all deals urls from main page and from submenus
        for url in elements_urls:
            if is_product(url):
                deals_urls.append(url)
            if ('/deal/' in url) or ('/browse/' in url):  # if an url leads to a submenu
                deals_urls = deals_urls + get_submenus_urls(url)  # add the deals from submenus

        print("All urls taken. Extracting the ids")

        product_ids = [extract_product_id(url) for url in deals_urls if
                       extract_product_id(url) is not None and extract_product_id(url) != '']
        return [*set(product_ids)]  # remove duplicates

    except Exception as e:
        print(e)
        return []  # error, no ids taken


def get_submenus_urls(submenu_url):
    # headers needed to avoid scraping blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.1 Safari/605.1.15', }
    submenu_page = requests.get(submenu_url, headers=headers)
    submenu_page_content = html.fromstring(submenu_page.content)

    # only deals which are present if cookies are not accepted (no suggestions at the bottom of the page)
    elements_urls = submenu_page_content.xpath('//a[contains(@class, "a-link-normal")]/@href')

    return [x for x in elements_urls if is_product(x)]  # remove all urls that are not deals (for example, share urls)


def is_product(url):  # products have /dp/ in their url
    return "/dp/" in url


def extract_product_id(url):
    return re.search('dp\/(.*?)(?=\/|\?)', url).group(1)


def url_from_id(product_id):
    return "https://www.amazon.it/dp/" + product_id


def get_product_info(product_id):
    # headers needed to avoid scraping blocking
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0', }
    params = {
        'th': '1',
        'psc': '1'
    }  # using params to not waste links where there are variants TODO
    product_page = requests.get(url_from_id(product_id), headers=headers, params=params)

    product_page_content = html.fromstring(product_page.content)

    try:
        # elements may not be found if the deal has variants (page has only price range) TODO (make only subscriptions not valid)
        title = product_page_content.xpath('//span[@id="productTitle"]/text()')[0].strip()
        old_price = product_page_content.xpath('//span[@data-a-strike="true"]//span[@aria-hidden="true"]/text()')[0]
        new_price = product_page_content.xpath('//span[contains(@class, "priceToPay")]//span[@class="a-offscreen"]/text()')[0]
        discount_rate = product_page_content.xpath('//span[contains(@class, "savingsPercentage")]/text()')[0]
        image_link = product_page_content.xpath('//img[@id="landingImage"]/@src')[0].split("._")[0] + ".jpg"  # remove latter part of image link to get the highest resolution

        return {
            "product_id": product_id,
            "title": title,
            "old_price": old_price,
            "new_price": new_price,
            "discount_rate": discount_rate,
            "image_link": image_link
        }

    except Exception as e:
        print("\nError for product id:\n\n" + product_id + "\n\nbecause:\n\n" + str(e) + "\n Probably strange formatting of webpage.\n")
        return None
