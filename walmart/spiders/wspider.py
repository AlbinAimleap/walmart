import json
import math
import scrapy
from urllib.parse import urlencode, urljoin
from pathlib import Path


def get_categories():
    filepath = Path(__file__).parent / 'category_links.json'
    with open(filepath, 'r') as f:
        category_links = json.load(f)
        return [i["url"].split("?")[0] for i in category_links]

class WalmartSpider(scrapy.Spider):
    name = "walmart"
    
    def start_requests(self):
        cats = get_categories()
        for url in cats[:1]:
            payload = {'page': 1, 'affinityOverride': 'default'}
            walmart_search_url = urljoin(url, '?' + urlencode(payload))
            print(walmart_search_url)
            yield scrapy.Request(url=walmart_search_url, callback=self.parse_search_results, meta={'page': 1, 'cat_url': url})

    def parse_search_results(self, response):
        cat_url = response.meta['cat_url']
        page = response.meta['page']
        script_tag  = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)

            ## Request Product Page
            product_list = json_blob["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["items"]
            for product in product_list:
                walmart_product_url = 'https://www.walmart.com' + product.get('canonicalUrl', '').split('?')[0]
                yield scrapy.Request(url=walmart_product_url, callback=self.parse_product_data, meta={'page': page, 'cat_url': cat_url})
                # yield scrapy.Request(url="https://www.walmart.com/ip/Time-and-Tru-Women-s-High-Rise-Jeggings-29-Inseam-Sizes-XS-XXXL/2414148269?classType=VARIANT&athbdg=L1300", callback=self.parse_product_data, meta={'page': page})
            
            # Request Next Page
            total_product_count = json_blob["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["count"]
            max_pages = math.ceil(total_product_count / 40)
            for p in range(2, max_pages):
                payload = {'page': p, 'affinityOverride': 'default'}
                walmart_search_url = urljoin(cat_url, '?' + urlencode(payload))
                yield scrapy.Request(url=walmart_search_url, callback=self.parse_search_results, meta={'page': p, 'cat_url': cat_url})
    
    
    def parse_product_data(self, response):
        script_tag  = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)
            raw_product_data = json_blob["props"]["pageProps"]["initialData"]["data"]["product"]
            if raw_product_data.get("promo"):
                with open('walmart_data_4.json', 'w') as f:
                    json.dump(raw_product_data, f)
            print(raw_product_data.get('canonicalUrl'))
            sale_price = raw_product_data.get('priceInfo', {}).get('currentPrice', {}).get('price', '')
            regular_price = raw_product_data.get('priceInfo', {}).get('wasPrice', {}).get('price') if raw_product_data.get('priceInfo') and raw_product_data.get('priceInfo').get('wasPrice') else ''
            data = {
                'id': raw_product_data.get('id'),
                'type': raw_product_data.get('type'),
                'name': raw_product_data.get('name'),
                'brand': raw_product_data.get('brand'),
                'averageRating': raw_product_data.get('averageRating'),
                'manufacturerName': raw_product_data.get('manufacturerName'),
                'shortDescription': raw_product_data.get('shortDescription'),
                'thumbnailUrl': raw_product_data.get('imageInfo', {}).get('thumbnailUrl'),
                'sale_price': sale_price or regular_price,
                'regular_price': regular_price or sale_price,
                'currencyUnit': raw_product_data.get('priceInfo', {}).get('currentPrice', {}).get('currencyUnit', ''),
                'discounts': raw_product_data.get('discounts'),
                'promo_data': raw_product_data.get('promo_data'),
                'promo_discount': raw_product_data.get('promoDiscount'),
            }
                
            yield data
