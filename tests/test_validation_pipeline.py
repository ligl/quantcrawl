import pytest
from scrapy.exceptions import DropItem

from quantcrawl.pipelines import ValidationPipeline


def test_validation_pipeline_drop_missing_fields() -> None:
    pipeline = ValidationPipeline()
    with pytest.raises(DropItem):
        pipeline.process_item({"source": "a"}, spider=None)


def test_validation_pipeline_ok() -> None:
    pipeline = ValidationPipeline()
    item = {
        "source": "a",
        "dataset": "b",
        "event_time": "2026-01-01T00:00:00+00:00",
        "collected_at": "2026-01-01T00:00:00+00:00",
        "raw_payload_hash": "x",
    }
    assert pipeline.process_item(item, spider=None) == item
