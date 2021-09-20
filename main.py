import bs4
import requests
import argparse
import re
import sys
import json
import csv
import asyncio

# PATHS
URL_BASE = 'https://urbanauctions.ca'
EVENT_BASE = 'Event/Details'
LOT_BASE = 'Event/LotDetails'

def setup() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('event_id', type=str)
    parser.add_argument('--json', type=str, help='Save results in json format to [JSON]')

    return parser.parse_args()

def get_items(event_id: str) -> list:
    page = 0
    items = []
    def get_soup(event_id: str, page: int) -> bs4.BeautifulSoup:
        content = requests.get(f"{URL_BASE}/{EVENT_BASE}/{event_id}?page={page}").content
        return bs4.BeautifulSoup(content, 'html.parser')

    soup = get_soup(event_id, page)
    
    while soup.find_all('div', attrs={'class': 'galleryUnit'}):
        for a in soup.find_all('a', attrs={'href': True}):
            if re.search('^/Event/LotDetails/\d+', a['href']) is not None:
                url = f"{URL_BASE}{a['href']}"
                if url not in items:
                    print(f"Found listing: {url}", file=sys.stderr)
                    items.append(url)
        page = page + 1
        soup = get_soup(event_id, page)

    return items

async def get_page_items(url: str) -> list:
    items = []
    content = requests.get(url).content
    soup = bs4.BeautifulSoup(content, 'html.parser')
    for a in soup.find_all('a', attrs={'href': True}):
            if re.search('^/Event/LotDetails/\d+', a['href']) is not None:
                _url = f"{URL_BASE}{a['href']}"
                if _url not in items:
                    print(f"{url}: {_url}", file=sys.stderr)
                    items.append(_url)
    return items

def get_item_info(url: str) -> dict:
    content = requests.get(url).content
    soup = bs4.BeautifulSoup(content, 'html.parser')

    # Item info fields are broken out into their own functions for improved readability/maintainablity
    # Most are done with CSS path selectors because the site doesn't really have much in the way of well labeled elements.

    def get_title() -> str:
        selector = 'html body main div.container div div.row div.col-xs-12.col-md-7.detail__title__wrapper h3.detail__title'
        return soup.select_one(selector).text.strip()

    def get_bid() -> str:
        selector = 'html body main div.container div div.row div.col-xs-12.col-md-7 div.panel.panel-default.closed-details ul.list-group li.list-group-item span.NumberPart'
        return soup.select_one(selector).text.strip()

    def get_high_bidder() -> str:
        selector = 'html body main div.container div div.row div.col-xs-12.col-md-7 div.panel.panel-default.closed-details ul.list-group li.list-group-item'
        return soup.select_one(selector).text.split()[-1].strip()

    def get_seller() -> str:
        selector = 'html body main div.container div div.row div.col-xs-12.col-md-7 div.detail__seller-data div.seller-data__container div.seller-data__summary div.detail__user-summary span.bb strong'
        return soup.select_one(selector).text.strip()

    def get_lot_num() -> str:
        for li in soup.find_all('li'):
            text = re.sub('\s+', ' ', li.text)
            if text.startswith('Lot # '):
                return text.split()[-1].strip()

    def get_system_id() -> str:
        for li in soup.find_all('li'):
            text = re.sub('\s+', ' ', li.text)
            if text.startswith('System ID # '):
                return text.split()[-1].strip()

    def get_start_date() -> str:
        for span in soup.find_all('span', attrs={'class': 'awe-rt-startingDTTM'}):
            return span['data-initial-dttm'].strip()

    def get_end_date() -> str:
        for span in soup.find_all('span', attrs={'class': 'awe-rt-endingDTTM'}):
            return span['data-initial-dttm'].strip()

    def get_desc() -> str:
        selector = 'html body main div.container div div.row div.col-xs-12.col-md-7 div.panel.panel-default.detail__description-panel div.panel-body.description'
        return soup.select_one(selector).text.split()[-1].strip()

    def get_num_bids() -> str:
        for i in soup.find_all('li', attrs={'class': 'list-group-item'}):
            if re.search('^\d+ Bid\(s\).+', i.text.strip()) is not None:
                text = re.sub('\s+', ' ', i.text)
                return text.split()[0]

    return {
        'url': url,
        'title': get_title(),
        'bid': get_bid(),
        'num_bids': get_num_bids(),
        'high_bidder': get_high_bidder(),
        'seller': get_seller(),
        'lot_num': get_lot_num(),
        'system_id': get_system_id(),
        'start_date': get_start_date(),
        'end_date': get_end_date(),
        'desc': get_desc()
    }

async def main():
    args = setup()
    print(args)

    # Get last page number    
    content = requests.get(f"{URL_BASE}/{EVENT_BASE}/{args.event_id}").content
    soup = bs4.BeautifulSoup(content, 'html.parser')
    pages = []
    for a in soup.find_all('a', attrs={'href': True}):
        if re.search('^/Event/Details/\d+\?page=\d+', a['href']) is not None:
            pages.append(a['href'])
    pages = sorted(pages)
    pages = int(pages[-1].split('=')[-1])
    del content, soup

    # Build master list of lot URLs
    items_url_list = []
    r = await asyncio.gather(*[get_page_items(f"{URL_BASE}/{EVENT_BASE}/{args.event_id}?page={page}") for page in range(1)])
    for url_list in r:
        for url in url_list:
            items_url_list.append(url)

    # Build list of item details
    # TODO: Implement asyncio
    items = []
    for index, url in enumerate(items_url_list):
        print(f"[{index/len(items_url_list):7.2%}] Getting details for listing: {url}", file=sys.stderr)
        items.append(get_item_info(url))

    if args.json:
        json.dump(items, open(args.json, 'w', encoding='utf-8'), sort_keys=True, indent=4, separators=(',', ': '))

    csvwriter = csv.writer(sys.stdout, delimiter=',', quotechar='"',quoting=csv.QUOTE_NONNUMERIC)
    csvwriter.writerow(items[0].keys())
    for itemno in range(len(items)):
        csvwriter.writerow(items[itemno].values())
        
if __name__ == '__main__':
    asyncio.run(main())