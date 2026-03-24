from __future__ import annotations

SPIDER_NAME = "demo_spider"

POLICY_PROFILE: dict[str, object] = {
    "header_profile": {
        "referer": "http://www.czce.com.cn/",
    },
    "challenge_enabled": False,
}

PIPELINES: dict[str, int] = {
    "quantcrawl.jobs.demo_spider.pipeline.DemoSpiderPipeline": 250,
}

