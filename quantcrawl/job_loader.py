from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
JOBS_DIR = PACKAGE_DIR / "jobs"


@dataclass(frozen=True, slots=True)
class JobConfig:
    job_name: str
    spider_name: str
    policy_profile: dict[str, object]
    pipelines: dict[str, int]
    file_name: str


def _discover_job_names() -> set[str]:
    names: set[str] = set()
    for path in JOBS_DIR.iterdir():
        if not path.is_dir() or path.name.startswith("__"):
            continue
        if (path / "spider.py").exists():
            names.add(path.name)
    return names


def _discover_config_paths() -> list[Path]:
    return sorted(
        path / "config.py"
        for path in JOBS_DIR.iterdir()
        if (path / "config.py").exists()
    )


def _load_module_from_path(path: Path) -> object:
    module_name = f"quantcrawl.jobs._loaded_{path.parent.name}_config"
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load job config module: {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_pipeline_map(job_name: str, pipelines: object, file_name: str) -> dict[str, int]:
    if not isinstance(pipelines, dict):
        raise ValueError(f"{file_name}: PIPELINES must be dict[str, int] for job={job_name}")
    output: dict[str, int] = {}
    for pipeline_path, priority in pipelines.items():
        if not isinstance(pipeline_path, str) or not pipeline_path.strip():
            raise ValueError(f"{file_name}: pipeline path must be non-empty str for job={job_name}")
        if type(priority) is not int:
            raise ValueError(f"{file_name}: pipeline priority must be int for {pipeline_path}")
        output[pipeline_path] = priority
    return output


@lru_cache(maxsize=1)
def _load_job_configs() -> dict[str, JobConfig]:
    job_names = _discover_job_names()
    config_paths = _discover_config_paths()

    if not config_paths:
        raise ValueError(
            f"No job config files found in {JOBS_DIR}. "
            "Each job requires jobs/<job_name>/config.py.",
        )

    loaded: dict[str, JobConfig] = {}
    for path in config_paths:
        module = _load_module_from_path(path)
        file_name = f"jobs/{path.parent.name}/config.py"
        expected_name = path.parent.name

        spider_name = getattr(module, "SPIDER_NAME", None)
        if not isinstance(spider_name, str) or not spider_name.strip():
            raise ValueError(f"{file_name}: SPIDER_NAME must be a non-empty str")
        if spider_name != expected_name:
            raise ValueError(
                f"{file_name}: SPIDER_NAME={spider_name!r} must match job directory name "
                f"{expected_name!r}",
            )
        if spider_name in loaded:
            raise ValueError(
                f"{file_name}: duplicate SPIDER_NAME={spider_name!r} already declared in "
                f"{loaded[spider_name].file_name}",
            )

        policy_profile = getattr(module, "POLICY_PROFILE", None)
        if not isinstance(policy_profile, dict):
            raise ValueError(f"{file_name}: POLICY_PROFILE must be dict[str, object]")

        pipelines = _validate_pipeline_map(
            job_name=expected_name,
            pipelines=getattr(module, "PIPELINES", None),
            file_name=file_name,
        )

        loaded[spider_name] = JobConfig(
            job_name=expected_name,
            spider_name=spider_name,
            policy_profile=dict(policy_profile),
            pipelines=pipelines,
            file_name=file_name,
        )

    configured = set(loaded.keys())
    missing = job_names - configured
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(
            "Missing job config file(s) for job module(s): "
            f"{names}. Expected jobs/<job_name>/config.py.",
        )

    extra = configured - job_names
    if extra:
        names = ", ".join(sorted(extra))
        raise ValueError(
            "Job config exists but spider module is missing for: "
            f"{names}. Remove stale job config(s).",
        )

    return loaded


def build_spider_profiles() -> dict[str, dict[str, object]]:
    configs = _load_job_configs()
    return {name: dict(config.policy_profile) for name, config in configs.items()}


def build_spider_pipelines() -> dict[str, int]:
    configs = _load_job_configs()
    pipelines: dict[str, int] = {}
    declared_by: dict[str, str] = {}
    for config in configs.values():
        for pipeline_path, priority in config.pipelines.items():
            owner = declared_by.get(pipeline_path)
            if owner is not None:
                raise ValueError(
                    "Duplicate pipeline path declared in job configs: "
                    f"{pipeline_path} (owners: {owner}, {config.spider_name})",
                )
            declared_by[pipeline_path] = config.spider_name
            pipelines[pipeline_path] = priority
    return pipelines
