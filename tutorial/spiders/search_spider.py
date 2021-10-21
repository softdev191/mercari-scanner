import scrapy
import json
import logging
from bs4 import BeautifulSoup
import urllib.parse as urlparse
from urllib.parse import parse_qs
from twisted.internet import reactor
from twisted.internet.defer import Deferred

class SearchSpider(scrapy.Spider):
    name = 'search'
    keyword = ''
    Q = None
    firstScan = True

    def __init__(self, **kwargs):
        self.base_url = 'https://www.mercari.com'
        self.count = 0
        self.page = 1
        self.max_page = 1
        self.oldItems = []
        
        super().__init__(**kwargs)

    def start_requests(self):
        self.Q.put('Start')
        yield self.mercari_scapy_request()
        
    def mercari_scapy_request(self):
        return scrapy.Request(
            'https://www.mercari.com/jp/search/?sort_order=created_desc&keyword={}'.format(self.keyword),
            method="GET",
            callback=self.parse,
            dont_filter = True
        )
    def parse(self, response):
        div_item = '//section[has-class("items-box")]'
        div_search_result = response.xpath('//div[has-class("search-result-number")]').get()
        if div_search_result is not None:
            items = response.xpath(div_item).getall()
            for item in items:
                pItem = BeautifulSoup(item, 'html.parser')
                vName = pItem.select_one('.items-box-name').get_text()
                vPrice = pItem.select_one('.items-box-price').get_text()
                vPhoto = pItem.select_one('.items-box-photo img')['data-src']
                vLink = '{}{}'.format(self.base_url, pItem.select_one('a')['href'])
                newItem = {
                    'name': vName,
                    'link': vLink,
                    'price': vPrice,
                    'image': vPhoto,
                    'type': 'list'
                }
                exist = False
                for oi in self.oldItems:
                    if oi['link'] == newItem['link']:
                        exist = True
                if exist != True:
                    self.Q.put(json.dumps(newItem))
                    if self.firstScan != True:
                        yield scrapy.Request(
                            vLink,
                            method="GET",
                            callback=self.parse_item,
                            dont_filter = True
                        )
        self.Q.put('Scrapped')
        self.firstScan = False
        # yield self.mercari_scapy_request()
    def parse_item(self, response):
        try:
            h_name = '//h1[has-class("item-name")]/text()'
            name = response.xpath(h_name).get()

            span_price = '//span[has-class("item-price")]/text()'
            price = response.xpath(span_price).get()

            table_info = '//table[has-class("item-detail-table")]'
            info = response.xpath(table_info).get()
            pInfo = BeautifulSoup(info, 'html.parser')
            trs = pInfo.select('tr')
            seller = trs[0].select_one('td').select_one('a').get_text()
            like_count = trs[0].select_one('td').select('.item-user-ratings')[0].select_one('span').get_text()
            dislike_count = trs[0].select_one('td').select('.item-user-ratings')[1].select_one('span').get_text()

            itemObj = {
                'link': response.request.url,
                'name': name,
                'seller': seller,
                'price': price,
                'like_count': like_count,
                'dislike_count': dislike_count,
                'type': 'item'
            }
            self.Q.put(json.dumps(itemObj))
        except:
            print('aaa')
    def close(self, reason):
        self.Q.put('Stop')