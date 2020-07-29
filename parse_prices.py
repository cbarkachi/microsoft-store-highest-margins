from bs4 import BeautifulSoup
import requests
import re
import urllib
import tabulate
from tqdm import tqdm

MICROSOFT_DOMAIN = 'https://www.microsoft.com'
LISTING_SUBDOMAINS = [
    '/en-us/store/collections/pcdeals?cat0=Devices',
    '/en-us/store/collections/businessdevices?icid=Cnavbusinesslist&HeaderID=department-windows',
    '/en-us/store/b/shop-all-pcs?IsDeal=true&price=0To500',
    '/en-us/store/b/shop-all-pcs?IsDeal=true&price=500To1000',
    '/en-us/store/b/shop-all-pcs?IsDeal=true&price=1000To1500',
    '/en-us/store/b/shop-all-pcs?IsDeal=true&price=1500To2000',
    '/en-us/store/b/shop-all-pcs?IsDeal=true&price=2000To'
]

computers = {}


def process_general_page(subdomain):
    print('Processing subdomain: ' + subdomain)
    url = MICROSOFT_DOMAIN + subdomain
    request = requests.get(url)
    soup = BeautifulSoup(request.content, 'html.parser')

    for listing in tqdm(soup.select('.m-channel-placement-item.f-wide.f-full-bleed-image')):
        process_listing(listing)


def process_listing(listing):
    computer = {}
    title = listing.find('h3').decode_contents()
    price = float(listing.find(itemprop='price').decode_contents().replace(
        '$', '').replace(',', ''))
    listing_subdomain = listing.a.attrs['href']
    listing_request = requests.get(MICROSOFT_DOMAIN + listing_subdomain)
    page_soup = BeautifulSoup(listing_request.content, 'html.parser')
    page_text = page_soup.text
    page_split = page_text.split('Model number')
    model_number = '.'
    if len(page_split) > 1:
        model_number = page_split[1].split()[1].replace(
            ':', '').replace('s:', '').replace(',', '')
    computer['MS Price'] = price
    computer['Model #'] = model_number
    computers[title] = computer


def check_ebay_prices():
    print()
    print("Comparing with eBay's prices...")
    for computer_name in tqdm(computers):
        computer = computers[computer_name]
        if computer['Model #'] != '.':
            result_mn = parse_ebay_prices(computer['Model #'])
        else:
            result_title = parse_ebay_prices(computer_name)
        total_num_matches = result_mn[0]
        sum_prices = result_mn[1]
        computer['eBay Min'] = result_mn[2]
        computer['eBay Max'] = result_mn[3]
        if total_num_matches == 0:
            computer['eBay Average'] = '.'
            computer['Margin (%)'] = 0
        else:
            average = sum_prices / total_num_matches
            microsoft_price = computer['MS Price']
            margin_percentage = (average - microsoft_price) / average * 100
            computer['eBay Average'] = average
            computer['Margin (%)'] = margin_percentage
        computer['# Listings'] = total_num_matches


def parse_ebay_prices(search_query):
    ebay_url = 'https://www.ebay.com/sch/i.html?_from=R40&_nkw=' + \
        urllib.parse.quote(
            search_query) + '&_sacat=0&LH_Sold=1&LH_Complete=1&rt=nc&LH_ItemCondition=3'
    r = requests.get(ebay_url)
    soup = BeautifulSoup(r.content, 'html.parser')
    item_list = soup.find(id='mainContent')
    good_results = str(item_list).split('Results matching fewer words')[0]
    price_pattern = re.compile('<span class="s-item__price">[^\d]+\d+\.\d+')
    matches = re.findall(price_pattern, good_results)
    total_num_matches = len(matches)
    sum_prices = 0
    min_price, max_price = float('inf'), float('-inf')
    for match in matches:
        price = float(match.split('$')[-1].strip())
        sum_prices += price
        min_price = min(min_price, price)
        max_price = max(max_price, price)
    return total_num_matches, sum_prices, min_price if min_price != float('inf') else '.', max_price if max_price != float('-inf') else '.'


def get_best_deals():
    computer_keys = list(computers.keys())
    computer_keys.sort(
        key=lambda computer: computers[computer]['Margin (%)'], reverse=True)
    header = ['Name'] + list(computers[computer_keys[0]].keys())
    rows = [[computer] + list(computers[computer].values())
            for computer in computer_keys]
    print(tabulate.tabulate(rows, header))


if __name__ == '__main__':
    for subdomain in LISTING_SUBDOMAINS:
        process_general_page(subdomain)
    check_ebay_prices()
    get_best_deals()
