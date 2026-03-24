#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <job_name>"
  echo "Example: $0 funding_rate"
  exit 1
fi

job_name="$1"

if [[ ! "$job_name" =~ ^[a-z][a-z0-9_]*$ ]]; then
  echo "Error: <job_name> must be snake_case (lowercase letters, numbers, underscores), starting with a letter."
  exit 1
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

job_dir="quantcrawl/jobs/${job_name}_spider"
job_init_file="${job_dir}/__init__.py"
items_file="${job_dir}/item.py"
loaders_file="${job_dir}/loader.py"
pipelines_file="${job_dir}/pipeline.py"
spiders_file="${job_dir}/spider.py"
job_config_file="${job_dir}/config.py"

if [[ -e "$job_dir" ]]; then
  echo "Error: job directory already exists: $job_dir"
  exit 1
fi

for path in "$items_file" "$loaders_file" "$pipelines_file" "$spiders_file" "$job_config_file"; do
  if [[ -e "$path" ]]; then
    echo "Error: file already exists: $path"
    exit 1
  fi
done

class_base="$(echo "$job_name" | awk -F'_' '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1' OFS='')"

mkdir -p "$job_dir"

cat > "$job_init_file" <<INIT
from .spider import ${class_base}Spider

__all__ = ["${class_base}Spider"]
INIT

cat > "$items_file" <<ITEM
from __future__ import annotations

import scrapy

from quantcrawl.items.base import BaseDataItem


class ${class_base}Item(BaseDataItem):
    title = scrapy.Field()
    content = scrapy.Field()
    attributes = scrapy.Field()
ITEM

cat > "$loaders_file" <<LOADER
from __future__ import annotations

from itemloaders.processors import MapCompose

from quantcrawl.loaders.base import BaseDataLoader
from quantcrawl.loaders.processors import clean_text


class ${class_base}Loader(BaseDataLoader):
    title_in = MapCompose(clean_text)
    content_in = MapCompose(clean_text)
LOADER

cat > "$pipelines_file" <<PIPE
from __future__ import annotations

from typing import Any


class ${class_base}Pipeline:
    def process_item(self, item: Any, spider: Any) -> Any:
        if getattr(spider, "name", "") != "${job_name}_spider":
            return item
        return item
PIPE

cat > "$spiders_file" <<SPIDER
from __future__ import annotations

from typing import Any

import scrapy

from quantcrawl.jobs.${job_name}_spider.item import ${class_base}Item
from quantcrawl.jobs.${job_name}_spider.loader import ${class_base}Loader
from quantcrawl.spiders.base import BaseSpider


class ${class_base}Spider(BaseSpider):
    name = "${job_name}_spider"
    allowed_domains = ["www.czce.com.cn", "czce.com.cn"]
    start_urls = ["http://www.czce.com.cn/"]
    source = "${job_name}_source"
    dataset = "${job_name}_dataset"

    def parse_list(self, response: scrapy.http.Response) -> Any:
        loader = ${class_base}Loader(item=${class_base}Item(), response=response)
        loader.add_value("source", self.source)
        loader.add_value("dataset", self.dataset)
        loader.add_value("symbol_or_topic", "homepage")
        loader.add_value("url_or_endpoint", response.url)
        loader.add_value("event_time", "")
        loader.add_value("collected_at", "")

        title = response.css("title::text").get(default="${class_base} Demo")
        payload = {
            "title": title,
            "content": title,
            "attributes": {"site": "${class_base}", "page_type": "homepage"},
        }
        normalized = self.build_common_item(payload)

        loader.add_value("raw_payload_hash", normalized["raw_payload_hash"])
        loader.add_value("title", payload["title"])
        loader.add_value("content", payload["content"])
        loader.add_value("attributes", payload["attributes"])
        loader.add_value("metadata", payload["attributes"])
        yield loader.load_item()

    def parse_detail(self, response: scrapy.http.Response) -> Any:
        return None
SPIDER

cat > "$job_config_file" <<CONF
from __future__ import annotations

SPIDER_NAME = "${job_name}_spider"

POLICY_PROFILE: dict[str, object] = {
    "header_profile": {
        "referer": "http://www.czce.com.cn/",
    },
    "challenge_enabled": False,
}

PIPELINES: dict[str, int] = {
    "quantcrawl.jobs.${job_name}_spider.pipeline.${class_base}Pipeline": 250,
}
CONF

echo "Created:"
echo "  $job_init_file"
echo "  $items_file"
echo "  $loaders_file"
echo "  $pipelines_file"
echo "  $spiders_file"
echo "  $job_config_file"
echo
echo "Next steps:"
echo "1. Adjust files under ${job_dir}/"
echo "2. Run: uv run scrapy list"
echo "3. Run: uv run scrapy crawl ${job_name}_spider"
