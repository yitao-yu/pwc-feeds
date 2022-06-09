import logging

from pwc import config
from pwc.feed import Feed

import re

emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               #u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)

log = logging.getLogger(__name__)

if __name__ == '__main__':
    for feed_type in config.FEED_TYPES:
        feed = Feed(feed_type)
        # feed.feed().decode()
        try:
            rss_feed = feed.feed().decode()
            
            rss_feed = emoji_pattern.sub(r'', rss_feed) # remove emoji(hugging face typical)
            
            path = './rss/'+feed_type+'.xml'
            
            # write to path
            f = open(path, "w") 
            f.write(rss_feed)
            f.close()
        except Exception as e:
            log.info(e)
            continue
