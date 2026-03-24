#!/usr/bin/env bash
set -euo pipefail

export APP_ENV="${APP_ENV:-dev}"
uv run scrapy crawl demo_spider
