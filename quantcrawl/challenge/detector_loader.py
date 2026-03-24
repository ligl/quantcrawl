from __future__ import annotations

from importlib import import_module

from .detector import ChallengeDetector


def _load_detector_class(detector_path: str, spider_name: str) -> type[object]:
    if "." not in detector_path:
        raise ValueError(
            "Invalid detector class path for spider "
            f"{spider_name!r}: {detector_path!r}. Expected 'pkg.module.ClassName'.",
        )

    module_path, class_name = detector_path.rsplit(".", 1)
    try:
        module = import_module(module_path)
    except Exception as exc:  # pragma: no cover - import errors are environment-dependent.
        raise ValueError(
            f"Failed to import detector module for spider {spider_name!r}: {module_path!r}",
        ) from exc

    try:
        detector_class = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(
            "Detector class not found for spider "
            f"{spider_name!r}: {detector_path!r}",
        ) from exc

    if not isinstance(detector_class, type):
        raise ValueError(
            f"Detector target must be a class for spider {spider_name!r}: {detector_path!r}",
        )
    return detector_class


def _validate_detector_protocol(instance: object, spider_name: str, detector_path: str) -> None:
    detect_fn = getattr(instance, "detect", None)
    if not callable(detect_fn):
        raise ValueError(
            "Detector does not implement detect(request, response, policy) for spider "
            f"{spider_name!r}: {detector_path!r}",
        )


def build_spider_detectors(
    spider_profiles: dict[str, dict[str, object]],
) -> dict[str, ChallengeDetector]:
    detectors: dict[str, ChallengeDetector] = {}
    for spider_name, profile in spider_profiles.items():
        detector_ref = str(profile.get("challenge_detector_ref", "")).strip()
        if not detector_ref:
            continue

        detector_class = _load_detector_class(detector_ref, spider_name=spider_name)
        try:
            instance = detector_class()
        except Exception as exc:  # pragma: no cover - detector constructors are custom.
            raise ValueError(
                "Failed to initialize challenge detector for spider "
                f"{spider_name!r} with class {detector_ref!r}",
            ) from exc
        _validate_detector_protocol(instance, spider_name=spider_name, detector_path=detector_ref)
        detectors[spider_name] = instance # type: ignore
    return detectors
