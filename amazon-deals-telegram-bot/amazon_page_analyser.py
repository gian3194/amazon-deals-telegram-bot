from selenium import webdriver

from selenium.webdriver.chrome.service import Service  # handle chrome driver
from selenium.webdriver.common.by import By  # get element by

from webdriver_manager.chrome import \
    ChromeDriverManager  # automatically download the correct version of the chrome driver
from subprocess import CREATE_NO_WINDOW  # do not open terminal when creating selenium instance

import re  # use regex for selecting product id in link
import time  # wait until new page loaded


import re  #use regex for selecting product id in link
import time  #wait until new page loaded

import requests  # lighter way to retrieve informations from html only (no js and css loaded)
from lxml import html


def start_selenium():
    chrome_options = webdriver.ChromeOptions()  # add the debug options you need
    chrome_options.add_argument("--headless")  # do not open chrome gui
    chrome_options.add_argument('--disable-gpu')  # disable hardware acceleration for compatibility reasons

    # download the most up-to-date chrome driver
    chrome_service = Service(ChromeDriverManager().install())
    chrome_service.creationflags = CREATE_NO_WINDOW

    # create a Chrome tab with the selected options
    chrome_driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    return chrome_driver


def get_deals_urls(selenium_driver):
    deals_page = "https://www.amazon.it/deals/"

    print("Starting taking all urls")

    try:
        selenium_driver.get(deals_page)

        # go to page with 50% or more discount
        selenium_driver.execute_script("arguments[0].click();",
                                       selenium_driver.find_element(By.LINK_TEXT, "Sconto del 50% o più"))

        # get all deals (products and submenus)
        elements_urls = []
        emergency_counter = 0

        while(len(elements_urls) == 0):  #wait until pages loads the products with the wanted discount
            #get all urls with <a> tag with a css class that contains 'DealCard'. There are both immediate deals and submenus with deals
            elements_urls = [e.get_attribute("href") for e in seleniumDriver.find_elements(By.CSS_SELECTOR, "a[class*='DealCard']")]
            time.sleep(0.5)

            emergency_counter += 1  #avoid infinte loop if page does not load
            if(emergency_counter > 120):
                raise Exception("Error loading products in deals page")

        deals_urls = []  # store all deals from main page and deals submenus
        for url in elements_urls:
            if is_product(url):
                deals_urls.append(url)
            if ('/deal/' in url) or ('/browse/' in url):  # if an url leads to a submenu
                deals_urls = deals_urls + get_submenus_deals_urls(url)  # add the deals urls from the submenus

        print("All urls taken")

        return remove_duplicate_by_id(deals_urls)

    except Exception as e:
        print(e)


def get_submenus_deals_urls(submenu_url):
    #headers needed to avoid scraping blocking
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0',}
    submenu_page = requests.post(submenu_url, headers=headers)
    submenu_page.raise_for_status()

    submenu_page_content = html.fromstring(submenu_page.content)

    # only the deals are present if cookies are not accepted (no suggestions at the bottom of the page)
    elements_urls = submenu_page_content.xpath('//a[contains(@class, "a-link-normal")]/@href')  # TODO: not all links may be taken

    for url in elements_urls.copy():  # remove all urls that are not deals (for example, share urls)
        if not is_product(url):
            elements_urls.remove(url)

    return elements_urls


def is_product(url):  # products on sale have /dp/ in their link
    return "/dp/" in url


def remove_duplicate_by_id(urls):
    for url in urls.copy():
        product_id = re.search('dp\/(.*?)(?=\/|\?)', url).group(1)  # id between 'dp\' and ('?' or '\')

        count = 0  # remove url if same id present more than once
        for url in urls:
            if product_id in url:
                if count == 0:
                    count += 1
                else:
                    urls.remove(url)
    return urls


def get_product_info(product_url):

    #headers needed to avoid scraping blocking
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0',}
    product_page = requests.post(product_url, headers=headers)
    product_page.raise_for_status()

    product_page_content = html.fromstring(product_page.content)

    product_id = re.search('dp\/(.*?)(?=\/|\?)', product_url).group(1)

    try:
        # elements may not be found if the deal is only for a subscription, if the deal ended or if there are options
        title = product_page_content.xpath('//span[@id="productTitle"]/text()')[0].strip()
        old_price = product_page_content.xpath('//span[@data-a-strike="true"]//span[@aria-hidden="true"]/text()')[0]
        new_price = product_page_content.xpath('//span[contains(@class, "priceToPay")]//span[@class="a-offscreen"]/text()')[0]
        discount_rate = product_page_content.xpath('//span[contains(@class, "savingsPercentage")]/text()')[0]
        image_link = product_page_content.xpath('//img[@id="landingImage"]/@src')[0]

        return {
            "product_id": product_id,
            "title": title,
            "old_price": old_price,
            "new_price": new_price,
            "discount_rate": discount_rate,
            "image_link": image_link
        }

    except Exception as e:
        print("Error at link:\n\n" + product_url + "\n\nbecause:\n\n" + str(e))
        return None
