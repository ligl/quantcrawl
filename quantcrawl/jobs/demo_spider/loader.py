from __future__ import annotations

from itemloaders.processors import MapCompose

from quantcrawl.loaders.base import BaseDataLoader
from quantcrawl.loaders.processors import clean_text


class DemoSpiderLoader(BaseDataLoader):
    title_in = MapCompose(clean_text)
    content_in = MapCompose(clean_text)

