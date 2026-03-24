from __future__ import annotations

import scrapy

from quantcrawl.items.base import BaseDataItem


class DemoSpiderItem(BaseDataItem):
    title = scrapy.Field()
    content = scrapy.Field()
    attributes = scrapy.Field()

