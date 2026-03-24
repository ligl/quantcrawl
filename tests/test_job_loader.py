from __future__ import annotations

from pathlib import Path

import pytest

import quantcrawl.job_loader as jl


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_loader_cache() -> None:
    jl._load_job_configs.cache_clear()
    yield
    jl._load_job_configs.cache_clear()


def _patch_jobs_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(jl, "JOBS_DIR", jobs_dir)
    return jobs_dir


def _create_job(
    jobs_dir: Path,
    job_name: str,
    spider_name: str,
    policy_profile: str = "{}",
    pipelines: str = "{}",
) -> None:
    _write(jobs_dir / job_name / "spider.py", "class X: pass\n")
    _write(
        jobs_dir / job_name / "config.py",
        "\n".join(
            [
                f'SPIDER_NAME = "{spider_name}"',
                f"POLICY_PROFILE = {policy_profile}",
                f"PIPELINES = {pipelines}",
            ],
        )
        + "\n",
    )


def test_build_profiles_and_pipelines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    jobs_dir = _patch_jobs_dir(monkeypatch, tmp_path)
    _create_job(
        jobs_dir=jobs_dir,
        job_name="demo_spider",
        spider_name="demo_spider",
        policy_profile='{"challenge_enabled": False}',
        pipelines='{"quantcrawl.jobs.demo_spider.pipeline.DemoSpiderPipeline": 250}',
    )

    assert jl.build_spider_profiles() == {"demo_spider": {"challenge_enabled": False}}
    assert jl.build_spider_pipelines() == {
        "quantcrawl.jobs.demo_spider.pipeline.DemoSpiderPipeline": 250,
    }


def test_missing_config_for_job_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    jobs_dir = _patch_jobs_dir(monkeypatch, tmp_path)
    _write(jobs_dir / "demo_spider" / "spider.py", "class X: pass\n")

    with pytest.raises(ValueError, match="No job config files found|Missing job config file"):
        jl.build_spider_profiles()


def test_stale_config_without_spider_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    jobs_dir = _patch_jobs_dir(monkeypatch, tmp_path)
    _write(
        jobs_dir / "demo_spider" / "config.py",
        "\n".join(
            [
                'SPIDER_NAME = "demo_spider"',
                "POLICY_PROFILE = {}",
                "PIPELINES = {}",
            ],
        )
        + "\n",
    )

    with pytest.raises(ValueError, match="spider module is missing"):
        jl.build_spider_profiles()


def test_spider_name_must_match_job_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    jobs_dir = _patch_jobs_dir(monkeypatch, tmp_path)
    _create_job(
        jobs_dir=jobs_dir,
        job_name="demo_spider",
        spider_name="other_spider",
    )

    with pytest.raises(ValueError, match="must match job directory name"):
        jl.build_spider_profiles()


def test_policy_profile_must_be_dict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    jobs_dir = _patch_jobs_dir(monkeypatch, tmp_path)
    _create_job(
        jobs_dir=jobs_dir,
        job_name="demo_spider",
        spider_name="demo_spider",
        policy_profile="[]",
    )

    with pytest.raises(ValueError, match="POLICY_PROFILE must be dict"):
        jl.build_spider_profiles()


def test_pipeline_priority_must_be_int(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    jobs_dir = _patch_jobs_dir(monkeypatch, tmp_path)
    _create_job(
        jobs_dir=jobs_dir,
        job_name="demo_spider",
        spider_name="demo_spider",
        pipelines='{"quantcrawl.jobs.demo_spider.pipeline.DemoSpiderPipeline": "250"}',
    )

    with pytest.raises(ValueError, match="pipeline priority must be int"):
        jl.build_spider_profiles()


def test_duplicate_pipeline_paths_raise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    jobs_dir = _patch_jobs_dir(monkeypatch, tmp_path)
    _create_job(
        jobs_dir=jobs_dir,
        job_name="a_spider",
        spider_name="a_spider",
        pipelines='{"quantcrawl.jobs.shared.pipeline.SharedPipeline": 250}',
    )
    _create_job(
        jobs_dir=jobs_dir,
        job_name="b_spider",
        spider_name="b_spider",
        pipelines='{"quantcrawl.jobs.shared.pipeline.SharedPipeline": 260}',
    )

    with pytest.raises(ValueError, match="Duplicate pipeline path"):
        jl.build_spider_pipelines()

