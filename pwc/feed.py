from functools import lru_cache
import json
import logging
from typing import cast, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError

from cachetools.func import ttl_cache
from feedgen.feed import FeedGenerator
from humanize import naturalsize
from lxml.etree import CDATA
from more_itertools import unique_everseen
from bs4 import BeautifulSoup as bs


from pwc import config

# baseurl = 'https://paperswithcode.com'

config.configure_logging()

log = logging.getLogger(__name__)

def extract_rule(text):
    soup = bs(text.decode(),features="lxml")
    rs = soup.find_all('div', class_='col-lg-9 item-col')
    
    extracted_items = []
    for item in rs:
        title_soup = item.find('h1').find('a')
        abstract_soup = item.find('p', class_='item-strip-abstract')
        
        title = title_soup.string
        itemurl = config.baseurl+str(title_soup).split("\"")[1]
        
        # if they use an onclick, alien url
        if str(title_soup).split("\"")[1].startswith('http'):
            itemurl = str(title_soup).split("\"")[1]
        
        abstract = abstract_soup.string
        extracted_items.append({"title":title,
                                "url":itemurl,
                                "abstract":abstract})
    return extracted_items

class Feed:

    def __init__(self, feed_type: str):
        html_url_suffix = feed_type if feed_type != "trending" else ''
        html_urls = [f'{config.HTML_URL_BASE}{html_url_suffix}?page={page_num}' for page_num in
                     range(1, config.NUM_PAGES_READ[feed_type] + 1)]
        self._html_requests = [Request(html_url, headers={'User-Agent': config.USER_AGENT}) for html_url in html_urls]

        self._feed_type = feed_type
        self._feed_type_desc = f'for "{self._feed_type}"'
        self._feed_title = config.FEED_TITLE_TEMPLATE.format(feed_type=self._feed_type.title())

        self._is_debug_logged = log.isEnabledFor(logging.DEBUG)

        self._output = lru_cache(maxsize=1)(self._output)  # type: ignore  # Instance level cache
        self.feed = ttl_cache(maxsize=1, ttl=config.CACHE_TTL)(self.feed)  # type: ignore  # Instance level cache

    def _init_feed(self) -> FeedGenerator:
        feed = FeedGenerator()
        feed.title(self._feed_title)
        feed.link(href=config.REPO_URL, rel='self')
        feed.description(config.FEED_DESCRIPTION)
        return feed

    def _output(self, texts: Tuple[bytes, ...]) -> bytes:
        feed_type_desc = self._feed_type_desc
        items = [item for text in texts for item in extract_rule(text)]
        items = list(unique_everseen(items, json.dumps))
        log.info('HTML inputs %s have %s items in all.', feed_type_desc, len(items))
        
        feed = self._init_feed()
        is_debug_logged = self._is_debug_logged
        
        # adapt here
        for item in items:
            # for website in ("https://github.com/", "https://gitlab.com/"):
            #     if item["code_link"].startswith(website):
            #         item["code_author"] = item["code_link"].removeprefix(website).split("/")[0]
            #         item["title"] = "/" + item["code_author"] + "/ " + item["title"]
            #         break
            # if 'categories' not in item:
            #     item['categories'] = []
            # elif isinstance(item['categories'], str):
            #     item['categories'] = [item['categories']]

            entry = feed.add_entry(order='append')
            entry.title(item['title'])
            entry.link(href=item['url'])
            entry.guid(item['url'], permalink=True)
            # description = '\n\n'.join((item['description'], item['code_link']))
            description = f'{item["abstract"]}' #<p>Code: <a href="{item["code_link"]}">{item["code_link"]}</a></p>'
            entry.description(CDATA(description))
            # entry.comments(item["code_link"])
            # for category in item['categories']:
            #     if category.startswith('+') and category[1:].isdigit():  # Ex: +1, +2
            #         continue
            #     category = category.capitalize() if category.isupper() else category
            #     entry.category(term=category)
            if is_debug_logged:
                log.debug('Added: %s', item['title'])

        text_: bytes = feed.rss_str(pretty=True)
        log.info('XML output %s has %s items.', feed_type_desc, text_.count(b'<item>'))
        return text_

    def feed(self) -> bytes:
        feed_type_desc = self._feed_type_desc
        log.debug(f'Reading %s HTML pages %s.', len(self._html_requests), feed_type_desc)
        
        error = True
        attempt_count = 0
        while(error):
            try:
                texts = tuple(cast(bytes, urlopen(html_request).read()) for html_request in self._html_requests)
                error = False
            except URLError as e:
                import time
                attempt_count+= 1
                time.sleep(5)
                if attempt_count>=3:
                    log.info('failure: URLError,', feed_type_desc,', timed out')
                    raise e
                    break
                
            
        log.info('HTML inputs %s have sizes: %s', feed_type_desc, ', '.join(humanize_len(text) for text in texts))
        ##
        text = self._output(texts)
        log.info('XML output %s has size %s.', feed_type_desc, humanize_len(text))
        return text


def humanize_len(text: bytes) -> str:
    return naturalsize(len(text), gnu=True, format='%.0f')
