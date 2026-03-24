from __future__ import annotations

import scrapy


class BaseDataItem(scrapy.Item):
    source = scrapy.Field()
    dataset = scrapy.Field()
    symbol_or_topic = scrapy.Field()
    event_time = scrapy.Field()
    collected_at = scrapy.Field()
    url_or_endpoint = scrapy.Field()
    raw_payload_hash = scrapy.Field()
    metadata = scrapy.Field()
