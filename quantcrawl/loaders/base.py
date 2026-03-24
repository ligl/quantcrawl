from __future__ import annotations

from itemloaders.processors import Identity, MapCompose, TakeFirst
from scrapy.loader import ItemLoader

from .processors import clean_text, normalize_url, to_utc_iso


class BaseDataLoader(ItemLoader):
    default_output_processor = TakeFirst()

    source_in = MapCompose(clean_text)
    dataset_in = MapCompose(clean_text)
    symbol_or_topic_in = MapCompose(clean_text)
    event_time_in = MapCompose(to_utc_iso)
    collected_at_in = MapCompose(to_utc_iso)
    url_or_endpoint_in = MapCompose(normalize_url)
    raw_payload_hash_in = MapCompose(clean_text)
    metadata_out = Identity()
