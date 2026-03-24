from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from quantcrawl.challenge.detector_loader import build_spider_detectors


def _write_module(tmp_path: Path, module_name: str, body: str) -> str:
    path = tmp_path / f"{module_name}.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return module_name


def test_build_spider_detectors_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = _write_module(
        tmp_path,
        "custom_detector_mod",
        """
        class DemoDetector:
            def detect(self, request, response, policy):
                return None
        """,
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    detectors = build_spider_detectors(
        spider_profiles={
            "demo_spider": {"challenge_detector_ref": f"{module_name}.DemoDetector"},
        },
    )
    assert "demo_spider" in detectors


def test_build_spider_detectors_raises_on_import_error() -> None:
    with pytest.raises(ValueError, match="Failed to import detector module"):
        build_spider_detectors(
            spider_profiles={
                "demo_spider": {"challenge_detector_ref": "missing.mod.Detector"},
            },
        )


def test_build_spider_detectors_raises_when_protocol_not_implemented(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = _write_module(
        tmp_path,
        "bad_detector_mod",
        """
        class DemoDetector:
            pass
        """,
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(ValueError, match="does not implement detect"):
        build_spider_detectors(
            spider_profiles={
                "demo_spider": {"challenge_detector_ref": f"{module_name}.DemoDetector"},
            },
        )
